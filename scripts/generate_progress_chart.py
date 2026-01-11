#!/usr/bin/env python3
"""
Script to generate an SVG progress bar/chart showing daily word count progress in .tex files.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


def generate_progress_svg(history: dict, output_path: Path) -> None:
    """Generate an SVG showing daily word count progress."""
    daily_counts = history.get("daily_counts", [])

    if not daily_counts:
        # Generate empty state
        svg_content = generate_empty_svg()
    else:
        svg_content = generate_chart_svg(daily_counts)

    output_path.write_text(svg_content)
    print(f"Generated SVG at {output_path}")


def generate_empty_svg() -> str:
    """Generate an SVG for when there's no data."""
    return """<svg xmlns="http://www.w3.org/2000/svg" width="400" height="120" viewBox="0 0 400 120">
  <style>
    .title { font: bold 14px sans-serif; fill: #24292f; }
    .subtitle { font: 12px sans-serif; fill: #57606a; }
  </style>
  <rect width="400" height="120" fill="#f6f8fa" rx="6"/>
  <text x="200" y="50" class="title" text-anchor="middle">📝 LaTeX Writing Progress</text>
  <text x="200" y="75" class="subtitle" text-anchor="middle">No data yet. Start writing!</text>
</svg>"""


def generate_chart_svg(daily_counts: list) -> str:
    """Generate an SVG bar chart showing daily word counts."""
    # Chart dimensions
    width = 500
    height = 200
    padding = 40
    chart_width = width - 2 * padding
    chart_height = height - 2 * padding - 30  # Extra space for title

    # Calculate daily changes (words added compared to previous day)
    changes = []
    for i, entry in enumerate(daily_counts):
        if i == 0:
            changes.append({"date": entry["date"], "change": 0, "total": entry["words"]})
        else:
            prev_words = daily_counts[i - 1]["words"]
            change = entry["words"] - prev_words
            changes.append({"date": entry["date"], "change": change, "total": entry["words"]})

    # Get max values for scaling
    max_change = max(abs(c["change"]) for c in changes) if changes else 1
    if max_change == 0:
        max_change = 1

    latest_total = daily_counts[-1]["words"] if daily_counts else 0
    today_change = changes[-1]["change"] if changes else 0

    # Calculate bar width based on number of entries
    num_bars = len(changes)
    bar_width = min(20, (chart_width - 10) / max(num_bars, 1))
    bar_gap = 2

    # Generate bars
    bars_svg = []
    for i, entry in enumerate(changes):
        x = padding + i * (bar_width + bar_gap)
        change = entry["change"]

        if change >= 0:
            # Positive change: bar goes up from middle
            bar_height = (change / max_change) * (chart_height / 2 - 10) if max_change > 0 else 0
            y = padding + 30 + chart_height / 2 - bar_height
            color = "#2ea44f"  # Green
        else:
            # Negative change: bar goes down from middle
            bar_height = (abs(change) / max_change) * (chart_height / 2 - 10) if max_change > 0 else 0
            y = padding + 30 + chart_height / 2
            color = "#cf222e"  # Red

        bars_svg.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{max(bar_height, 1):.1f}" fill="{color}" rx="2">'
            f'<title>{entry["date"]}: {change:+d} words (total: {entry["total"]})</title></rect>'
        )

    # Generate zero line
    zero_y = padding + 30 + chart_height / 2
    zero_line = f'<line x1="{padding}" y1="{zero_y}" x2="{width - padding}" y2="{zero_y}" stroke="#d0d7de" stroke-width="1"/>'

    # Today's summary
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if today_change > 0:
        change_text = f"+{today_change} words today! 📈"
        change_color = "#2ea44f"
    elif today_change < 0:
        change_text = f"{today_change} words today 📉"
        change_color = "#cf222e"
    else:
        change_text = "No change today"
        change_color = "#57606a"

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <style>
    .title {{ font: bold 14px sans-serif; fill: #24292f; }}
    .subtitle {{ font: 12px sans-serif; fill: #57606a; }}
    .total {{ font: bold 18px sans-serif; fill: #24292f; }}
    .change {{ font: bold 12px sans-serif; fill: {change_color}; }}
    .label {{ font: 10px sans-serif; fill: #57606a; }}
  </style>
  <rect width="{width}" height="{height}" fill="#ffffff" rx="6" stroke="#d0d7de"/>

  <!-- Title -->
  <text x="{padding}" y="25" class="title">📝 LaTeX Writing Progress</text>

  <!-- Stats -->
  <text x="{width - padding}" y="20" class="total" text-anchor="end">{latest_total:,} words</text>
  <text x="{width - padding}" y="35" class="change" text-anchor="end">{change_text}</text>

  <!-- Chart area -->
  {zero_line}
  {''.join(bars_svg)}

  <!-- Labels -->
  <text x="{padding}" y="{height - 10}" class="label">Last {len(daily_counts)} days</text>
  <text x="{width - padding}" y="{height - 10}" class="label" text-anchor="end">Updated: {today_str}</text>
</svg>"""

    return svg


def main():
    script_dir = Path(__file__).parent.parent
    history_file = script_dir / "data" / "word_count_history.json"
    output_file = script_dir / "assets" / "tex_progress.svg"

    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if history_file.exists():
        with open(history_file, "r") as f:
            history = json.load(f)
    else:
        print(f"Warning: No history file found at {history_file}")
        history = {"daily_counts": []}

    generate_progress_svg(history, output_file)

    return 0


if __name__ == "__main__":
    exit(main())
