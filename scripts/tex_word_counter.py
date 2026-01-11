#!/usr/bin/env python3
"""
Script to count words in .tex files across all GitHub repositories.
Requires a GitHub Personal Access Token with repo scope for private repositories.
"""

import os
import re
import json
import tempfile
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests


def get_all_repos(token: str, username: str) -> list[dict]:
    """Fetch all repositories (including private) for the authenticated user."""
    repos = []
    page = 1
    per_page = 100

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    while True:
        url = f"https://api.github.com/user/repos?per_page={per_page}&page={page}&affiliation=owner"
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()
        if not data:
            break

        repos.extend(data)
        page += 1

    return repos


def count_words_in_tex_content(content: str) -> int:
    """Count words in TeX content, excluding comments and commands."""
    # Remove comments (lines starting with %)
    content = re.sub(r"%.*$", "", content, flags=re.MULTILINE)

    # Remove common LaTeX commands but keep their text content
    # Remove \command{} but keep content inside braces for text commands
    content = re.sub(r"\\(textbf|textit|emph|underline)\{([^}]*)\}", r"\2", content)

    # Remove other LaTeX commands
    content = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^}]*\})?", " ", content)

    # Remove math environments
    content = re.sub(r"\$[^$]+\$", " ", content)
    content = re.sub(r"\\\[.*?\\\]", " ", content, flags=re.DOTALL)
    content = re.sub(r"\\begin\{(equation|align|math|displaymath)\*?\}.*?\\end\{\1\*?\}", " ", content, flags=re.DOTALL)

    # Remove braces
    content = re.sub(r"[{}]", " ", content)

    # Split by whitespace and count non-empty words
    words = [w for w in content.split() if w]

    return len(words)


def clone_and_count_tex_words(repo: dict, token: str) -> int:
    """Clone a repository and count words in all .tex files."""
    total_words = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir) / repo["name"]

        # Use git with credential in header to avoid token in URL/logs
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"

        # Build authenticated URL - git suppresses credentials in output when using capture_output
        # This is the standard approach used in CI environments
        clone_url = repo["clone_url"].replace(
            "https://github.com/", f"https://x-access-token:{token}@github.com/"
        )

        try:
            # Clone with depth 1 for efficiency
            result = subprocess.run(
                ["git", "clone", "--depth", "1", "--quiet", clone_url, str(repo_path)],
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
            )

            if result.returncode != 0:
                print(f"  Warning: Could not clone {repo['name']}: {result.stderr}")
                return 0

            # Find all .tex files
            tex_files = list(repo_path.rglob("*.tex"))

            for tex_file in tex_files:
                try:
                    content = tex_file.read_text(encoding="utf-8", errors="ignore")
                    words = count_words_in_tex_content(content)
                    total_words += words
                except Exception as e:
                    print(f"  Warning: Could not read {tex_file}: {e}")

            print(f"  {repo['name']}: {len(tex_files)} .tex files, {total_words} words")

        except subprocess.TimeoutExpired:
            print(f"  Warning: Timeout cloning {repo['name']}")
        except Exception as e:
            print(f"  Warning: Error processing {repo['name']}: {e}")

    return total_words


def load_history(history_file: Path) -> dict:
    """Load historical word count data."""
    if history_file.exists():
        with open(history_file, "r") as f:
            return json.load(f)
    return {"daily_counts": []}


def save_history(history_file: Path, history: dict) -> None:
    """Save historical word count data."""
    with open(history_file, "w") as f:
        json.dump(history, f, indent=2)


def main():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GH_TOKEN or GITHUB_TOKEN environment variable required")
        return 1

    # Get the username from the token
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    user_response = requests.get("https://api.github.com/user", headers=headers, timeout=30)
    user_response.raise_for_status()
    username = user_response.json()["login"]

    print(f"Fetching repositories for {username}...")
    repos = get_all_repos(token, username)
    print(f"Found {len(repos)} repositories")

    total_words = 0
    for repo in repos:
        words = clone_and_count_tex_words(repo, token)
        total_words += words

    print(f"\nTotal words in .tex files: {total_words}")

    # Save to history
    script_dir = Path(__file__).parent.parent
    history_file = script_dir / "data" / "word_count_history.json"
    history_file.parent.mkdir(parents=True, exist_ok=True)

    history = load_history(history_file)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Update or add today's count
    found = False
    for entry in history["daily_counts"]:
        if entry["date"] == today:
            entry["words"] = total_words
            found = True
            break

    if not found:
        history["daily_counts"].append({"date": today, "words": total_words})

    # Keep only the last 30 days
    history["daily_counts"] = sorted(history["daily_counts"], key=lambda x: x["date"])[-30:]

    save_history(history_file, history)
    print(f"History saved to {history_file}")

    return 0


if __name__ == "__main__":
    exit(main())
