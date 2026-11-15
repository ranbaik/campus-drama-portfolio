"""
주간 KPI 리포트 자동 생성 (샘플)
================================
'스타트업 데이터 분석 인턴' 장면의 증빙 코드입니다.
매주 엑셀로 4시간씩 손으로 정리하던 주간 지표 보고를, 이 스크립트 한 번으로 끝내도록 만든 것을
강의용으로 단순화했습니다. 외부 라이브러리 없이 파이썬 표준 라이브러리만 씁니다.

사용법
  python kpi_report.py                      # 데이터의 가장 최근 주(週) 리포트 생성
  python kpi_report.py --week 2025-W38      # 특정 주 리포트 생성
  python kpi_report.py --make-sample-data   # 샘플 데이터(data/daily_metrics.csv) 다시 만들기

결과물
  output/kpi_report_<주>.html   사람이 읽는 리포트 (표 + 일별 그래프 + 한 줄 요약)
  output/kpi_summary_<주>.csv   다음 단계(대시보드·메일)에 넘기는 요약 표
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import random
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "daily_metrics.csv"
OUT = ROOT / "output"

FIELDS = ["date", "signups", "active_users", "lessons_completed", "paid_conversions",
          "revenue_krw", "churned_users", "support_tickets"]


# ───────────────────────── 1. 데이터 읽기 ─────────────────────────

def load_rows(path: Path = DATA) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        rows = []
        for r in csv.DictReader(f):
            row = {k: int(v) for k, v in r.items() if k != "date"}
            row["date"] = dt.date.fromisoformat(r["date"])
            rows.append(row)
    return sorted(rows, key=lambda r: r["date"])


def iso_week(d: dt.date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def week_rows(rows: list[dict], week: str) -> list[dict]:
    return [r for r in rows if iso_week(r["date"]) == week]


def prev_week(week: str) -> str:
    y, w = week.split("-W")
    monday = dt.date.fromisocalendar(int(y), int(w), 1)
    return iso_week(monday - dt.timedelta(days=7))


# ───────────────────────── 2. 지표 계산 (12개) ─────────────────────────

@dataclass
class Kpi:
    key: str
    label: str
    value: float
    unit: str = ""
    higher_is_better: bool = True


def compute_kpis(rows: list[dict]) -> list[Kpi]:
    if not rows:
        raise ValueError("해당 주의 데이터가 없습니다.")
    s = lambda k: sum(r[k] for r in rows)  # noqa: E731
    days = len(rows)
    signups, paid, revenue = s("signups"), s("paid_conversions"), s("revenue_krw")
    active_avg = s("active_users") / days
    churned, lessons, tickets = s("churned_users"), s("lessons_completed"), s("support_tickets")
    peak = max(rows, key=lambda r: r["active_users"])
    return [
        Kpi("signups", "신규 가입", signups, "명"),
        Kpi("dau_avg", "일평균 활성 사용자", round(active_avg), "명"),
        Kpi("peak_dau", f"최고 활성일({peak['date']:%m/%d})", peak["active_users"], "명"),
        Kpi("lessons", "학습 완료", lessons, "건"),
        Kpi("lessons_per_user", "활성 사용자 1인당 학습", round(lessons / max(active_avg, 1) / days, 2), "건/일"),
        Kpi("paid", "유료 전환", paid, "명"),
        Kpi("conv_rate", "가입 대비 유료 전환율", round(paid / max(signups, 1) * 100, 1), "%"),
        Kpi("revenue", "매출", revenue, "원"),
        Kpi("arppu", "유료 사용자 1인당 매출", round(revenue / max(paid, 1)), "원"),
        Kpi("churned", "이탈", churned, "명", higher_is_better=False),
        Kpi("churn_rate", "활성 대비 이탈률", round(churned / max(active_avg, 1) * 100, 1), "%", higher_is_better=False),
        Kpi("tickets", "고객 문의", tickets, "건", higher_is_better=False),
    ]


def with_change(cur: list[Kpi], prev: list[Kpi] | None) -> list[tuple[Kpi, float | None]]:
    if not prev:
        return [(k, None) for k in cur]
    p = {k.key: k.value for k in prev}
    return [(k, None if not p.get(k.key) else round((k.value - p[k.key]) / p[k.key] * 100, 1)) for k in cur]


# ───────────────────────── 3. 리포트 만들기 ─────────────────────────

def fmt(v: float, unit: str) -> str:
    text = f"{v:,.0f}" if float(v).is_integer() else f"{v:,}"
    return f"{text}{unit}"


def headline(changes: list[tuple[Kpi, float | None]]) -> str:
    """전주 대비 가장 크게 좋아진 지표와 나빠진 지표를 한 줄로."""
    scored = [(k, c if k.higher_is_better else -c) for k, c in changes if c is not None]
    if not scored:
        return "비교할 전주 데이터가 없어 이번 주 수치만 정리했습니다."
    best = max(scored, key=lambda x: x[1])
    worst = min(scored, key=lambda x: x[1])
    raw = dict((k.key, c) for k, c in changes)
    return (f"가장 좋아진 지표는 ‘{best[0].label}’({raw[best[0].key]:+.1f}%), "
            f"주의가 필요한 지표는 ‘{worst[0].label}’({raw[worst[0].key]:+.1f}%)입니다.")


def bar_chart_svg(rows: list[dict]) -> str:
    w, h, pad = 560, 180, 28
    top = max(r["active_users"] for r in rows) * 1.15
    bw = (w - pad * 2) / len(rows)
    bars = []
    for i, r in enumerate(rows):
        bh = (h - pad * 2) * r["active_users"] / top
        x = pad + i * bw + bw * 0.18
        y = h - pad - bh
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw * 0.64:.1f}" height="{bh:.1f}" rx="4" fill="#e97a5c"/>'
            f'<text x="{x + bw * 0.32:.1f}" y="{y - 5:.1f}" font-size="11" text-anchor="middle" fill="#3a2a26">{r["active_users"]:,}</text>'
            f'<text x="{x + bw * 0.32:.1f}" y="{h - 9}" font-size="11" text-anchor="middle" fill="#8a7a74">{r["date"]:%m/%d}</text>'
        )
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="일별 활성 사용자">'
            f'<line x1="{pad}" y1="{h - pad}" x2="{w - pad}" y2="{h - pad}" stroke="#f3d6ca"/>{"".join(bars)}</svg>')


def render_html(week: str, rows: list[dict], changes: list[tuple[Kpi, float | None]]) -> str:
    def change_cell(k: Kpi, c: float | None) -> str:
        if c is None:
            return '<td class="muted">—</td>'
        good = (c >= 0) == k.higher_is_better
        return f'<td class="{"up" if good else "down"}">{"▲" if c >= 0 else "▼"} {abs(c):.1f}%</td>'

    trs = "\n".join(
        f"<tr><td>{html.escape(k.label)}</td><td class='num'>{fmt(k.value, k.unit)}</td>{change_cell(k, c)}</tr>"
        for k, c in changes
    )
    period = f"{rows[0]['date']:%Y.%m.%d} – {rows[-1]['date']:%m.%d}"
    generated = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>주간 KPI 리포트 {week}</title>
<style>
 body{{font-family:'Pretendard','Apple SD Gothic Neo','Malgun Gothic',sans-serif;background:#fff7f3;color:#3a2a26;margin:0;padding:24px}}
 main{{max-width:720px;margin:0 auto}} .card{{background:#fff;border-radius:18px;padding:20px 22px;margin:14px 0;box-shadow:0 2px 10px #f3d6ca}}
 h1{{font-size:22px;margin:0}} .muted{{color:#8a7a74}} .lead{{font-size:15px;line-height:1.6}}
 table{{width:100%;border-collapse:collapse;font-size:14px}} td{{padding:8px 6px;border-bottom:1px solid #fbe7df}}
 .num{{text-align:right;font-variant-numeric:tabular-nums}} .up{{color:#2f8f6f;text-align:right}} .down{{color:#c94a3a;text-align:right}}
</style></head><body><main>
<div class="card"><p class="muted">주간 KPI 리포트 · 자동 생성</p><h1>{week} ({period})</h1>
<p class="lead">{html.escape(headline(changes))}</p></div>
<div class="card"><b>핵심 지표 12개</b> <span class="muted">· 오른쪽은 전주 대비</span>
<table>{trs}</table></div>
<div class="card"><b>일별 활성 사용자</b>{bar_chart_svg(rows)}</div>
<p class="muted" style="font-size:12px">생성: {generated} · kpi_report.py (캠퍼스 드라마 포트폴리오 샘플)</p>
</main></body></html>"""


def write_outputs(week: str, rows: list[dict], changes: list[tuple[Kpi, float | None]]) -> tuple[Path, Path]:
    OUT.mkdir(exist_ok=True)
    html_path = OUT / f"kpi_report_{week}.html"
    csv_path = OUT / f"kpi_summary_{week}.csv"
    html_path.write_text(render_html(week, rows, changes), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig: 엑셀에서 한글이 안 깨짐
        w = csv.writer(f)
        w.writerow(["지표", "값", "단위", "전주 대비(%)"])
        for k, c in changes:
            w.writerow([k.label, k.value, k.unit, "" if c is None else c])
    return html_path, csv_path


# ───────────────────────── 샘플 데이터 ─────────────────────────

def make_sample_data(path: Path = DATA, start: dt.date = dt.date(2025, 9, 1), weeks: int = 3) -> None:
    """에듀테크 스타트업의 일별 지표를 흉내 낸 가상 데이터 (seed 고정 → 매번 같은 결과)."""
    rnd = random.Random(42)
    path.parent.mkdir(exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for i in range(weeks * 7):
            d = start + dt.timedelta(days=i)
            weekend = d.weekday() >= 5
            growth = 1 + i * 0.012
            active = int(rnd.gauss(1450, 60) * growth * (0.72 if weekend else 1))
            signups = int(rnd.gauss(85, 10) * growth * (0.6 if weekend else 1))
            paid = max(1, int(signups * rnd.uniform(0.07, 0.11)))
            w.writerow({
                "date": d.isoformat(), "signups": signups, "active_users": active,
                "lessons_completed": int(active * rnd.uniform(1.6, 2.1)),
                "paid_conversions": paid, "revenue_krw": paid * rnd.choice([19900, 29900, 49900]),
                "churned_users": int(rnd.gauss(14, 3)), "support_tickets": int(rnd.gauss(9, 2) * (0.5 if weekend else 1)),
            })


def main() -> None:
    ap = argparse.ArgumentParser(description="주간 KPI 리포트 자동 생성")
    ap.add_argument("--week", help="예: 2025-W38 (생략하면 데이터의 마지막 주)")
    ap.add_argument("--make-sample-data", action="store_true", help="샘플 데이터 다시 만들기")
    args = ap.parse_args()

    if args.make_sample_data or not DATA.exists():
        make_sample_data()
        print(f"샘플 데이터 생성: {DATA.relative_to(ROOT)}")

    rows = load_rows()
    week = args.week or iso_week(rows[-1]["date"])
    cur = week_rows(rows, week)
    prev = week_rows(rows, prev_week(week))
    changes = with_change(compute_kpis(cur), compute_kpis(prev) if prev else None)
    html_path, csv_path = write_outputs(week, cur, changes)
    print(headline(changes))
    print(f"리포트: {html_path.relative_to(ROOT)}\n요약표: {csv_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
