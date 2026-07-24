#!/usr/bin/env python3
"""Regenerate index.html by scanning the briefings/ directory.

Run from the repo root:
    python3 gen_index.py

Scans briefings/YYYY-MM-DD/ subdirectories, classifies each .html file by
prefix, and builds the landing page sorted newest-first.  Preserves the
how-it-works.html link and all static CSS/head content.

File classification (by filename prefix):
    briefing_*       → Daily Watchlist
    risk_audit_*     → Weekly Risk Audit
    proposal_*       → Order Proposals
    options_*        → Options Pilot
    (anything else)  → uses stem as label
"""
from __future__ import annotations
import os
import re
from datetime import date

BRIEFINGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "briefings")
INDEX_PATH    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

# Safety-scan pattern — must never appear in a file staged for public output
PRIVATE_RE = re.compile(
    r"692801525|787899301|PROP-|dollar_amount|deploy_today|"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}|<<<<<<<"
)

LABEL_MAP = {
    "briefing":    "Daily Watchlist",
    "risk_audit":  "Weekly Risk Audit",
    "proposal":    "Order Proposals",
    "options":     "Options Pilot",
}

HEAD = """\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>Trading Desk — Daily Briefings</title>
<style>
  :root { --bg:#0b0e14; --card:#141924; --line:#242c3a; --fg:#e6e9ef; --mut:#8b95a7; --acc:#4f9dff; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--fg);
         font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
  header { padding:32px 24px 16px; border-bottom:1px solid var(--line); }
  h1 { margin:0 0 6px; font-size:24px; letter-spacing:-.4px; }
  .sub { color:var(--mut); font-size:13px; }
  .note { margin:16px 24px 0; padding:12px 14px; background:#1a2130; border:1px solid var(--line);
           border-radius:8px; color:var(--mut); font-size:12.5px; }
  main { max-width:900px; margin:0 auto; padding:8px 24px 48px; }
  .day h2 { font-size:15px; color:var(--mut); font-weight:600; margin:28px 0 12px;
             text-transform:uppercase; letter-spacing:.5px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:12px; }
  .brief { display:flex; flex-direction:column; gap:6px; padding:16px; text-decoration:none;
            background:var(--card); border:1px solid var(--line); border-radius:10px; color:var(--fg);
            transition:border-color .15s, transform .15s; }
  .brief:hover { border-color:var(--acc); transform:translateY(-2px); }
  .list { font-weight:600; font-size:15px; }
  .ts { color:var(--mut); font-size:12px; font-variant-numeric:tabular-nums; }
  footer { color:var(--mut); font-size:12px; text-align:center; padding:24px; border-top:1px solid var(--line); }
</style>
</head>
<body>
<header>
  <h1>Daily Briefings</h1>
  <div class="sub">Three-pillar watchlist scans · newest first</div>
  <a href="how-it-works.html" style="display:inline-block;margin-top:12px;color:var(--acc);font-size:13px;text-decoration:none;">&#128214; New here? How this works, explained simply &rarr;</a>
</header>
<div class="note">Sanitized public view — ticker analysis &amp; pillar scores only.
  No account numbers, positions, or dollar figures. The full book, proposals, and
  ledger stay in the private repo and are reviewed locally.</div>
<main>
"""

FOOT_TMPL = """\
</main>
<footer>Generated {today} &middot; agentic-trading-desk</footer>
</body>
</html>
"""


def _label(stem: str) -> str:
    for prefix, label in LABEL_MAP.items():
        if stem.startswith(prefix):
            return label
    # fallback: titlecase the stem up to the first date-like token
    name = re.split(r"[_\-]20\d\d", stem)[0]
    return name.replace("_", " ").title()


def _ts(stem: str) -> str:
    """Extract the timestamp/date portion after the prefix."""
    m = re.search(r"(\d{4}-\d{2}-\d{2}.*)", stem)
    return m.group(1) if m else stem


def _label_order(stem: str) -> int:
    """Canonical card order within a day: watchlist → risk audit → proposals → options → rest."""
    order = ["briefing", "risk_audit", "proposal", "options"]
    for i, prefix in enumerate(order):
        if stem.startswith(prefix):
            return i
    return len(order)


def build_index(briefings_dir: str = BRIEFINGS_DIR) -> str:
    """Scan briefings/ and return the full index.html content."""
    # Collect {date_str: [(order, stem, rel_path), ...]}
    days: dict[str, list[tuple[int, str, str]]] = {}

    if not os.path.isdir(briefings_dir):
        return HEAD + FOOT_TMPL.format(today=date.today().isoformat())

    for entry in os.scandir(briefings_dir):
        if not entry.is_dir():
            continue
        day = entry.name  # expected: YYYY-MM-DD
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
            continue
        for fentry in os.scandir(entry.path):
            if not fentry.name.endswith(".html"):
                continue
            stem = fentry.name[:-5]  # strip .html
            rel  = f"briefings/{day}/{fentry.name}"
            days.setdefault(day, []).append((_label_order(stem), stem, rel))

    lines = [HEAD]
    for day in sorted(days.keys(), reverse=True):
        cards = sorted(days[day])  # sort by (order, stem) → deterministic
        lines.append(f'    <section class="day">\n      <h2>{day}</h2>\n      <div class="grid">')
        for _, stem, rel in cards:
            label = _label(stem)
            ts    = _ts(stem)
            lines.append(
                f'      <a class="brief" href="{rel}">\n'
                f'        <span class="list">{label}</span>\n'
                f'        <span class="ts">{ts}</span>\n'
                f'      </a>'
            )
        lines.append("      </div>\n    </section>")
    lines.append(FOOT_TMPL.format(today=date.today().isoformat()))
    return "\n".join(lines)


def safety_scan(content: str) -> list[str]:
    return PRIVATE_RE.findall(content)


def main() -> None:
    content = build_index()
    hits = safety_scan(content)
    if hits:
        raise SystemExit(f"ABORT: safety scan found private tokens: {hits!r}")
    with open(INDEX_PATH, "w", encoding="utf-8") as fh:
        fh.write(content)
    print(f"index.html regenerated ({content.count('<section')} day(s))")


if __name__ == "__main__":
    main()
