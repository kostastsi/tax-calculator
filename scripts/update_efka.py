#!/usr/bin/env python3
"""
Scrape current e-EFKA insurance contribution categories for new freelancers
and update the EFKA_CATEGORIES block in index.html.

Source: https://www.e-efka.gov.gr/el/asphalismenoi/me-misthotoi/neo-systhma-asfalistikon-eisforon/neoi-epaggelmaties

Usage:
  python3 scripts/update_efka.py            # update if changed; exit 0 always
  python3 scripts/update_efka.py --check    # exit 1 if changes pending (CI dry-run)

The script fails loudly (non-zero exit + stderr) when:
  - the page is unreachable
  - the table layout no longer matches expectations
  - extracted values fail sanity checks

This is intentional: we'd rather fail than silently write bad data.
"""

import argparse
import datetime as dt
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

EFKA_URL = (
    "https://www.e-efka.gov.gr/el/asphalismenoi/me-misthotoi/"
    "neo-systhma-asfalistikon-eisforon/neoi-epaggelmaties"
)
INDEX_HTML = Path(__file__).resolve().parent.parent / "index.html"
START_MARKER = "// === EFKA-CATEGORIES-START ==="
END_MARKER = "// === EFKA-CATEGORIES-END ==="
OAED_FIXED = 10.0  # €10/month flat OAED unemployment-fund contribution
USER_AGENT = "Mozilla/5.0 (compatible; tax-calculator-bot; +https://github.com/kostastsi/tax-calculator)"


class TableRowParser(HTMLParser):
    """Collects every <tr> as a list of cell text strings."""

    def __init__(self):
        super().__init__()
        self.in_td = False
        self.row = []
        self.rows = []
        self.buf = []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag == "td":
            self.in_td = True
            self.buf = []

    def handle_endtag(self, tag):
        if tag == "td" and self.in_td:
            self.row.append(" ".join("".join(self.buf).split()))
            self.in_td = False
        elif tag == "tr" and self.row:
            self.rows.append(self.row)

    def handle_data(self, data):
        if self.in_td:
            self.buf.append(data)


def fetch_page() -> str:
    req = urllib.request.Request(EFKA_URL, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        sys.exit(f"FATAL: could not fetch {EFKA_URL}: {e}")


def parse_amount(s: str) -> float:
    """Parse a Greek-formatted euro amount like '150,46' or '1.250,46'."""
    cleaned = s.replace("€", "").replace("€", "").strip()
    cleaned = cleaned.replace(".", "").replace(",", ".")
    return float(cleaned)


def extract_categories(html: str) -> list[dict]:
    """
    Returns a list of {id, name, monthly} dicts.

    Expects the page to contain table rows with exactly 4 cells:
      [label, pension_branch, health_branch, total]

    The 'special' row has label 'Ειδική...' and the regular rows have
    labels '1η' through '6η'. Other 4-cell rows are filtered out by label
    matching.
    """
    parser = TableRowParser()
    parser.feed(html)

    special = None
    regular = {}  # cat_number -> total

    for cells in parser.rows:
        if len(cells) != 4:
            continue
        label = cells[0]
        try:
            total = parse_amount(cells[3])
        except ValueError:
            continue

        if "Ειδική" in label or "Ειδικη" in label:
            special = total
        else:
            m = re.match(r"\s*([1-6])\s*η\b", label)
            if m:
                regular[int(m.group(1))] = total

    if special is None:
        sys.exit("FATAL: could not find special-category row (expected label containing 'Ειδική')")
    if sorted(regular.keys()) != [1, 2, 3, 4, 5, 6]:
        sys.exit(f"FATAL: expected categories 1..6, got {sorted(regular.keys())}")

    # Sanity: totals should be ascending and within plausible range
    totals = [special] + [regular[i] for i in range(1, 7)]
    for t in totals:
        if not (50 < t < 2000):
            sys.exit(f"FATAL: implausible category total {t} — page format may have changed")
    if regular[1] >= regular[6]:
        sys.exit(f"FATAL: category 1 ({regular[1]}) should be cheaper than category 6 ({regular[6]})")

    # Add €10 OAED to each
    return [
        {"id": "special", "name": "Ειδική (πρώτα 5 έτη)", "monthly": round(special + OAED_FIXED, 2)},
    ] + [
        {"id": str(i), "name": f"{i}η", "monthly": round(regular[i] + OAED_FIXED, 2)}
        for i in range(1, 7)
    ]


def render_block(year: int, categories: list[dict]) -> str:
    """Render the JS block between markers (markers themselves not included)."""
    lines = [
        f"const EFKA_YEAR = {year};",
        f"const EFKA_CATEGORIES_{year} = [",
    ]
    for cat in categories:
        # Quote the id and name; format monthly with 2 decimals
        lines.append(
            f'  {{ id: "{cat["id"]}", name: "{cat["name"]}", monthly: {cat["monthly"]:.2f} }},'
        )
    lines.append("];")
    return "\n".join(lines)


def replace_block(html_text: str, new_block: str) -> str:
    pattern = re.compile(
        re.escape(START_MARKER) + r"[^\n]*\n.*?\n" + re.escape(END_MARKER),
        re.DOTALL,
    )
    if not pattern.search(html_text):
        sys.exit(f"FATAL: could not find marker block in {INDEX_HTML.name}")
    replacement = (
        f"{START_MARKER} (auto-updated by scripts/update_efka.py — do not edit by hand)\n"
        f"{new_block}\n"
        f"{END_MARKER}"
    )
    return pattern.sub(lambda _: replacement, html_text, count=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if file would change; do not write")
    args = ap.parse_args()

    print(f"Fetching {EFKA_URL}", file=sys.stderr)
    html = fetch_page()
    categories = extract_categories(html)
    year = dt.date.today().year

    print(f"Parsed {len(categories)} categories for {year}:", file=sys.stderr)
    for c in categories:
        print(f"  {c['name']:<25} {c['monthly']:8.2f} €", file=sys.stderr)

    new_block = render_block(year, categories)
    current = INDEX_HTML.read_text(encoding="utf-8")
    updated = replace_block(current, new_block)

    if current == updated:
        print("No changes.", file=sys.stderr)
        return 0

    if args.check:
        print("Changes pending (run without --check to apply).", file=sys.stderr)
        return 1

    INDEX_HTML.write_text(updated, encoding="utf-8")
    print(f"Updated {INDEX_HTML}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
