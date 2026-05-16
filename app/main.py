from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

import FinanceDataReader as fdr


KST = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class IndexConfig:
    name: str
    symbol: str


INDICES = [
    IndexConfig("다우 산업", "DJI"),
    IndexConfig("나스닥 종합", "IXIC"),
    IndexConfig("상해 종합", "SSEC"),
    IndexConfig("니케이225", "N225"),
]


def parse_target_date(raw: str | None) -> date:
    if not raw or raw == "yesterday":
        return (datetime.now(KST).date() - timedelta(days=1))
    return datetime.strptime(raw, "%Y-%m-%d").date()


def latest_two_closes(symbol: str, target: date) -> tuple[float, float]:
    start = target - timedelta(days=14)
    end = target + timedelta(days=1)
    df = fdr.DataReader(symbol, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
    if df.empty or "Close" not in df.columns:
        raise RuntimeError(f"No close data for {symbol}")

    closes = df["Close"].dropna()
    closes = closes.loc[closes.index.date <= target]
    if len(closes) < 2:
        raise RuntimeError(f"Insufficient close data for {symbol}")

    latest = float(closes.iloc[-1])
    prev = float(closes.iloc[-2])
    return latest, prev


def format_change(curr: float, prev: float) -> str:
    pct = ((curr - prev) / prev) * 100
    if pct > 0:
        arrow = "▲"
    elif pct < 0:
        arrow = "▼"
    else:
        arrow = "-"
    return f"{arrow} {abs(pct):.2f}%"


def build_rows(target: date) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in INDICES:
        try:
            curr, prev = latest_two_closes(item.symbol, target)
            rows.append(
                {
                    "name": item.name,
                    "value": f"{curr:,.2f}",
                    "change": format_change(curr, prev),
                }
            )
        except Exception:
            rows.append({"name": item.name, "value": "N/A", "change": "N/A"})
    return rows


def render_html(target: date, rows: list[dict[str, str]]) -> str:
    tr_html = "\n".join(
        f"<tr><td>{r['name']}</td><td>{r['value']}</td><td>{r['change']}</td></tr>" for r in rows
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
      {tr_html}
    </tbody>
  </table>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-date", default="yesterday", help="YYYY-MM-DD or 'yesterday'")
    args = parser.parse_args()

    target = parse_target_date(args.target_date)
    rows = build_rows(target)

    reports = Path("reports")
    reports.mkdir(parents=True, exist_ok=True)

    out = reports / f"{target.isoformat()}.html"
    out.write_text(render_html(target, rows), encoding="utf-8")
    (reports / "latest.html").write_text(out.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"Generated: {out}")


if __name__ == "__main__":
    main()
