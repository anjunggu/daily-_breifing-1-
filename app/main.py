from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import FinanceDataReader as fdr

KST = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class IndexConfig:
    name: str
    symbol: str


INDICES: list[IndexConfig] = [
    IndexConfig("다우 산업", "DJI"),
    IndexConfig("나스닥 종합", "IXIC"),
    IndexConfig("상해 종합", "SSEC"),
    IndexConfig("니케이225", "N225"),
]


def parse_target_date(raw: str | None) -> date:
    if not raw or raw.strip() == "" or raw == "yesterday":
        return datetime.now(KST).date() - timedelta(days=1)
    return datetime.strptime(raw, "%Y-%m-%d").date()


def get_latest_and_previous_close(symbol: str, target: date) -> tuple[float, float]:
    start = target - timedelta(days=14)
    end = target + timedelta(days=1)
    df = fdr.DataReader(symbol, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    if df.empty or "Close" not in df.columns:
        raise ValueError(f"No data for {symbol}")

    closes = df["Close"].dropna()
    closes = closes.loc[closes.index.date <= target]

    if len(closes) < 2:
        raise ValueError(f"Not enough close data for {symbol}")

    current = float(closes.iloc[-1])
    previous = float(closes.iloc[-2])
    return current, previous


def format_change(current: float, previous: float) -> str:
    pct = ((current - previous) / previous) * 100
    if pct > 0:
        return f"▲ {pct:.2f}%"
    if pct < 0:
        return f"▼ {abs(pct):.2f}%"
    return "- 0.00%"


def build_rows(target: date) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for index in INDICES:
        try:
            current, previous = get_latest_and_previous_close(index.symbol, target)
            rows.append(
                {
                    "name": index.name,
                    "value": f"{current:,.2f}",
                    "change": format_change(current, previous),
                }
            )
        except Exception:
            rows.append({"name": index.name, "value": "N/A", "change": "N/A"})

    return rows


def render_html(target: date, rows: list[dict[str, str]]) -> str:
    body_rows = "\n".join(
        f"<tr><td>{row['name']}</td><td>{row['value']}</td><td>{row['change']}</td></tr>"
        for row in rows
    )

    return f"""<!doctype html>
<html lang=\"ko\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>일일 시장 요약 - {target.isoformat()}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; }}
    h1 {{ margin-bottom: 8px; }}
    table {{ border-collapse: collapse; width: 520px; max-width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    thead {{ background: #f6f6f6; }}
  </style>
</head>
<body>
  <h1>전일 시장 요약</h1>
  <p>기준일: {target.isoformat()}</p>
  <table>
    <thead>
      <tr><th>지수명</th><th>지수</th><th>등락</th></tr>
    </thead>
    <tbody>
      {body_rows}
    </tbody>
  </table>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate daily market HTML report")
    parser.add_argument("--target-date", default="yesterday", help="YYYY-MM-DD or yesterday")
    args = parser.parse_args()

    target = parse_target_date(args.target_date)
    rows = build_rows(target)

    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    dated_report = reports_dir / f"{target.isoformat()}.html"
    latest_report = reports_dir / "latest.html"

    html = render_html(target, rows)
    dated_report.write_text(html, encoding="utf-8")
    latest_report.write_text(html, encoding="utf-8")

    print(f"Generated report: {dated_report}")


if __name__ == "__main__":
    main()
