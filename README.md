# 캠퍼스 드라마 포트폴리오 (샘플: 홍길동)

‘캠퍼스 드라마’ 앱에서 기록한 장면으로 만든 포트폴리오와, 그 장면의 **증빙 자료**를 모아 둔 저장소입니다.
포트폴리오 PDF 속 링크가 이 저장소의 파일을 가리킵니다.

> 강의 시연용 샘플입니다. 인물·데이터는 모두 가상입니다.

## 구성

| 경로 | 내용 | 연결된 장면 |
|---|---|---|
| [`portfolio/홍길동_포트폴리오_샘플.pdf`](portfolio/) | 앱의 [📄 PDF 저장]으로 만든 포트폴리오 (A4, 3쪽) | 전체 |
| [`automation-sample/`](automation-sample/) | 주간 KPI 리포트 자동화 파이썬 코드 + 샘플 데이터 + 결과 예시 | 💼 스타트업 데이터 분석 인턴 (2025년 2학기) |
| [`.github/workflows/weekly-kpi.yml`](.github/workflows/weekly-kpi.yml) | 매주 월요일 자동 실행 (GitHub Actions) | 〃 |

## 포트폴리오 → 저장소 연결 방식

```
캠퍼스 드라마 앱 (장면 편집)
  └─ 증빙 자료: 링크 "자동화 코드(샘플)"  ──►  이 저장소 /automation-sample
                                         └─►  /automation-sample/output/kpi_report_2025-W38.html
포트폴리오 미리보기 → [📄 PDF 저장]  ──►  /portfolio/홍길동_포트폴리오_샘플.pdf
```

1. 장면에 증빙을 **파일**로 올리면 앱 안 ‘증빙 자료실’(내 기기)에 저장됩니다.
2. 남에게 보여 줄 증빙은 이런 저장소에 올리고, 장면에는 **링크**로 연결합니다.
3. 포트폴리오 PDF를 만들면 링크가 주소까지 함께 인쇄되어, 읽는 사람이 바로 찾아올 수 있습니다.

## 자동화 샘플 바로 실행

```bash
cd automation-sample
python kpi_report.py
```

자세한 내용은 [automation-sample/README.md](automation-sample/README.md)를 보세요.
