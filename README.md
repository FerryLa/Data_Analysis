
# Data Analysis

이 저장소는 **시장·산업·기업 데이터를 수집·정리·분석하여  
의사결정에 활용 가능한 인사이트로 전환하는 과정**을 정리한 데이터 분석 포트폴리오입니다.

뉴스, 거시 지표, **산업별 동향 및 주요 기업 분석 데이터**를 기반으로  
**KPI 정의 → 점수화 → 선별 → 시각화**의 흐름으로 분석을 수행합니다.

---

## Project Objective

- 비정형/정형 데이터를 활용한 **시장 관찰 및 분석 체계 구축**
- 뉴스·지표·산업·기업 데이터를 **KPI 관점에서 구조화**
- Power BI를 활용한 **시각적 인사이트 도출**
- 데이터 누적을 통한 **재사용 가능한 비즈니스 자산화**

---

## Directory Structure

```

Data_Analysis
├─ XXX_FolderName
│   ├─ data/
│   │  ├─ bronze/       # 원시 데이터 (Raw)
│   │  ├─ silver/       # 정제/전처리 데이터 (Processed)
│   │  └─ gold/         # 최종 비즈니스/보고용 데이터 (Curated)
│   │
│   ├─ governance/
│   │  ├─ catalog/      # 데이터 카탈로그 (메타데이터, 데이터셋 정의)
│   │  ├─ lineage/      # 데이터 계보(Lineage), ETL 흐름 문서화
│   │  ├─ quality/      # 데이터 품질 규칙, 검증 리포트
│   │  └─ policy/       # 접근 권한, 보안, 컴플라이언스 정책
│   │
│   ├─ notebooks/       # 탐색/분석용 노트북
│   │
│   ├─ powerbi/
│   │  ├─ dashboards/   # Power BI 대시보드 (.pbix)
│   │  └─ datasets/     # Power BI용 데이터 모델
│   │
│   ├─ docs/
│   │  ├─ private/     # 내부 전용 문서 (기밀, 상세 분석, 기술적 설명)
│   │  ├─ public/      # 외부 공유 문서 (이해관계자에게 공유 가능한 수준)
│   │  ├─ appendix/    # 추가자료 (부록, 보조 설명)
│   │  └─ Image/       # 보고서용 시각화 결과물
│   │
│   ├─ Release.md
│   └─ USER_Guide.md
│
├─ LICENSE
└─ README.md

```

---

## Data Sources

- **Market & Industry News**
  - 경제·산업 뉴스 (제목, 본문 요약, 키워드)
- **Company Analysis**
  - 주요 기업 뉴스, 이벤트, 실적 및 주가 변동 데이터
- **Macro Indicators**
  - CPI, 실업수당, 산업별 ETF
- **Industry Trends**
  - 산업별 흐름, 섹터 성과 비교, 구조적 변화 요인
- **Event Calendar**
  - 실적 발표, 주요 경제 지표, 컨퍼런스, 정책 이벤트

---

## Analysis Framework

본 프로젝트는 아래 프로세스를 기준으로 분석을 진행합니다.

**Collect → Organize → Observe → KPI Structuring → Insight**

### KPI 예시
- 구성원 관심도 (Interest Score)
- 이슈 중요도 (Importance Score)
- 시장 영향도 (Impact Score)
- 시의성 (Timeliness)

각 지표를 점수화하여 **“지금 봐야 할 산업·기업 이슈”만 선별하는 것을 목표로 합니다.**

---

## Power BI 활용

Power BI를 활용해 다음을 시각화합니다.

- 거시 지표 기반 시장 환경 대시보드
- 산업별 트렌드 및 섹터 비교
- 기업 이벤트·실적 기반 영향 분석
- KPI 점수 기반 뉴스·이슈 우선순위

> 단순 리포트가 아닌,  
> **의사결정을 지원하는 대시보드 설계**를 지향합니다.

---

## Key Insights

- 데이터는 소비 대상이 아니라 **판단 기준을 만들기 위한 재료**
- 뉴스·거시 지표·산업·기업 데이터를 결합할 때 **시장 구조가 선명해짐**
- KPI 기준이 명확할수록 **분석의 재현성과 신뢰도 향상**

---

## Tools & Skills

- Data Analysis: Python, Pandas, SQL
- Visualization: Power BI
- Documentation: Notion, Markdown
- Artificial Intelligence: MS Copilot, Claude Opus 4.5
- Version Control: Git / GitHub

---

## Future Plans

- 산업·기업 뉴스 스코어링 모델 고도화
- Power BI 자동 갱신 파이프라인 구축
- 데이터 기반 이슈 중요도 예측 실험
- 분석 결과를 전략·기획 관점으로 확장

---

**This repository is a living archive of market and industry observation for data-driven decision making.**
