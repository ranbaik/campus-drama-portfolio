"""
캡스톤: 캠퍼스 셔틀 대기시간 예측 (샘플)
=========================================
포트폴리오 장면 '캡스톤: 캠퍼스 셔틀 대기시간 예측'의 증빙 코드입니다.
6주 동안 정류장에서 손으로 기록한 승하차 데이터(약 2,400건)를 흉내 낸 가상 데이터로
'요일·시간·날씨·대기 인원'을 변수로 하는 선형 회귀 모델을 만들고 정확도를 확인합니다.
외부 라이브러리 없이 표준 라이브러리만 씁니다(최소제곱법을 직접 풀어 봄).

실행:  python shuttle_model.py
결과:  output/metrics.json, output/shuttle_slides.html (발표 자료 원본)
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "shuttle_log.csv"
OUT = ROOT / "output"
PEAK_HOURS = {8, 9, 17, 18}
TOLERANCE_MIN = 3  # 예측이 실제 대기와 ±3분 이내면 '정확한 안내'로 봄
FEATURES = ["절편", "대기 인원", "출퇴근 피크", "비", "월·금요일"]


# ───────────────────────── 1. 데이터 (가상) ─────────────────────────

def make_data(n_days: int = 30, seed: int = 7) -> list[dict]:
    """6주(평일 30일) × 하루 80회 관측 ≈ 2,400건."""
    rnd = random.Random(seed)
    rows, day = [], dt.date(2025, 3, 31)
    while len(rows) < n_days * 80:
        day += dt.timedelta(days=1)
        if day.weekday() >= 5:
            continue
        rain = rnd.random() < 0.25
        for _ in range(80):
            hour = rnd.choice(range(8, 20))
            peak = hour in PEAK_HOURS
            waiting = max(0, int(rnd.gauss(28 if peak else 12, 6)))
            wait = (2.0 + 0.12 * waiting + 4.0 * peak + 3.0 * rain + 1.2 * (day.weekday() in (0, 4))
                    + rnd.gauss(0, 2.1))
            rows.append({"date": day.isoformat(), "hour": hour, "waiting": waiting,
                         "rain": int(rain), "wait_min": round(max(wait, 0.5), 1)})
    DATA.parent.mkdir(exist_ok=True)
    with DATA.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return rows


def features(r: dict) -> list[float]:
    weekday = dt.date.fromisoformat(r["date"]).weekday()
    return [1.0, float(r["waiting"]), float(int(r["hour"]) in PEAK_HOURS), float(r["rain"]), float(weekday in (0, 4))]


# ───────────────────────── 2. 최소제곱 회귀 (직접 구현) ─────────────────────────

def solve(a: list[list[float]], b: list[float]) -> list[float]:
    """가우스 소거법으로 a·x = b 풀기."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[p] = m[p], m[c]
        for r in range(n):
            if r != c:
                f = m[r][c] / m[c][c]
                m[r] = [x - f * y for x, y in zip(m[r], m[c])]
    return [m[i][n] / m[i][i] for i in range(n)]


def fit(x: list[list[float]], y: list[float]) -> list[float]:
    k = len(x[0])
    xtx = [[sum(r[i] * r[j] for r in x) for j in range(k)] for i in range(k)]
    xty = [sum(r[i] * t for r, t in zip(x, y)) for i in range(k)]
    return solve(xtx, xty)  # β = (XᵀX)⁻¹ Xᵀy


def predict(beta: list[float], x: list[float]) -> float:
    return sum(b * v for b, v in zip(beta, x))


# ───────────────────────── 3. 평가 ─────────────────────────

def evaluate(rows: list[dict]) -> dict:
    rnd = random.Random(1)
    rows = rows[:]
    rnd.shuffle(rows)
    cut = int(len(rows) * 0.8)
    train, test = rows[:cut], rows[cut:]
    beta = fit([features(r) for r in train], [r["wait_min"] for r in train])
    errs = [predict(beta, features(r)) - r["wait_min"] for r in test]
    within = sum(abs(e) <= TOLERANCE_MIN for e in errs) / len(errs)
    mae = sum(abs(e) for e in errs) / len(errs)
    peak_actual = [r["wait_min"] for r in rows if int(r["hour"]) in PEAK_HOURS]
    return {
        "records": len(rows), "train": len(train), "test": len(test),
        "coefficients": {name: round(b, 3) for name, b in zip(FEATURES, beta)},
        "accuracy_within_3min": round(within * 100, 1),
        "mae_min": round(mae, 2),
        "avg_wait_peak_min": round(sum(peak_actual) / len(peak_actual), 1),
    }


# ───────────────────────── 4. 발표 자료(HTML → PDF) ─────────────────────────

def slides_html(m: dict) -> str:
    coef = "".join(f"<tr><td>{k}</td><td class='n'>{v:+.2f}분</td></tr>" for k, v in m["coefficients"].items() if k != "절편")
    slides = [
        ("캡스톤 디자인 2025-1", "캠퍼스 셔틀 대기시간 예측", "3인 팀 · 데이터 수집과 예측 모델 담당 · 홍길동 (가상 인물)"),
        ("1. 문제", "“셔틀이 언제 올지 몰라서 15분씩 기다려요”",
         "등하교 시간 셔틀 대기 불만이 학생 게시판에 매주 올라옴<br>→ 정류장 대기시간을 미리 알려 주면 줄을 덜 설 수 있지 않을까?"),
        ("2. 데이터", f"6주 동안 직접 기록한 {m['records']:,}건",
         "정류장별 대기 인원 · 시간대 · 요일 · 날씨(비) · 실제 대기시간(분)<br>평일 하루 80회, 조원 3명이 교대로 기록"),
        ("3. 모델", "대기시간 = 기본 + 인원·피크·비·요일 효과",
         f"<table>{coef}</table><p class='s'>선형 회귀(최소제곱법)를 직접 구현 · 학습 {m['train']:,}건 / 검증 {m['test']:,}건</p>"),
        ("4. 결과", f"안내 정확도 {m['accuracy_within_3min']:.0f}%",
         f"검증 데이터에서 예측이 실제와 ±{TOLERANCE_MIN}분 이내인 비율<br>평균 오차 {m['mae_min']}분<br>"
         "시범 운영 기간 평균 체감 대기 <b>12분 → 7분</b>"),
        ("5. 배운 점", "숫자 하나하나가 발품이었다",
         "데이터를 손으로 모으는 게 가장 힘들고 가장 중요했다<br>다음 목표: 실시간 위치 데이터 연동"),
    ]
    body = "".join(
        f"<section><p class='k'>{k}</p><h1>{h}</h1><div class='b'>{b}</div><p class='f'>캠퍼스 셔틀 대기시간 예측 · {i + 1}/{len(slides)}</p></section>"
        for i, (k, h, b) in enumerate(slides)
    )
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>캠퍼스 셔틀 대기시간 예측 — 발표 자료</title>
<style>
@page {{ size: 1280px 720px; margin: 0 }}
* {{ box-sizing: border-box }} body {{ margin: 0; word-break: keep-all; font-family: 'Malgun Gothic','Apple SD Gothic Neo',sans-serif; color: #3a2a26 }}
section {{ width: 1280px; height: 720px; padding: 90px 110px; position: relative; page-break-after: always;
  background: linear-gradient(135deg, #fff7f3, #ffd8c9) }}
.k {{ color: #c95c41; font-weight: 700; font-size: 22px; margin: 0 }} h1 {{ font-size: 56px; margin: 18px 0 36px; line-height: 1.25 }}
.b {{ font-size: 28px; line-height: 1.7 }} .s {{ font-size: 20px; color: #8a7a74 }} .f {{ position: absolute; bottom: 40px; right: 110px; color: #8a7a74; font-size: 16px }}
table {{ font-size: 26px; border-collapse: collapse }} td {{ padding: 6px 28px 6px 0 }} .n {{ font-weight: 700; color: #c95c41 }}
</style></head><body>{body}</body></html>"""


def main() -> None:
    rows = make_data()
    m = evaluate(rows)
    OUT.mkdir(exist_ok=True)
    (OUT / "metrics.json").write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "shuttle_slides.html").write_text(slides_html(m), encoding="utf-8")
    print(json.dumps(m, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
