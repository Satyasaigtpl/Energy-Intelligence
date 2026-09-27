# Energy Intelligence — Power BI portfolio

A historical electricity analytics case study built from **51,894,720 real customer readings**, with an auditable pipeline and a native Power BI report.

## Open the report

1. Open `Energy Intelligence/Energy Intelligence.pbix` in Power BI Desktop for the portable report with data. Open the `.pbip` alongside it when working with the source-controlled project.
2. Select **Home → Refresh** if the report opens without data.
3. Explore the four page tabs: consumption, demand, carbon scenarios and data quality.

The curated data is already prepared on this computer. If you move the repository, change the **DataFolder** text parameter in Transform data → Manage parameters to the absolute `data/curated/` folder, including the trailing slash, before refreshing. The PBIX already contains imported data for offline exploration. The editable source is PBIP/PBIR, the native Power BI project format.

## Business questions

| Dashboard | Audience | Decision supported |
|---|---|---|
| Consumption & customer portfolio | Energy account manager | Identify consumption patterns; distinguish onboarding growth from cohort trends |
| Peak demand & load performance | Operations analyst | Find portfolio peak periods and investigate flexible loads |
| Efficiency & carbon scenarios | Sustainability analyst | Explore energy-reduction targets under explicit carbon-factor assumptions |
| Data quality & interpretation | Analytics reviewer | Understand zeros, clock changes, fact grains and reconciliation |

## Source and rights

Artur Trindade (2015), **ElectricityLoadDiagrams20112014**, UCI Machine Learning Repository. DOI: [10.24432/C58C86](https://doi.org/10.24432/C58C86). [Dataset and documentation](https://archive.ics.uci.edu/dataset/321/electricity). Licensed **CC BY 4.0**. This project transforms and aggregates the original readings; attribution must accompany redistributions.

370 anonymized Portuguese customers, 140,256 quarter-hour timestamps, covering 2011–2014. These are historical observations, not current Portuguese grid performance. Source values are kW; interval energy is kW ÷ 4. Original timestamp labels run through the start of 2015; this project assumes end-of-interval labels and attributes readings to timestamp minus 15 minutes.

## Reproduce

Use Python 3.11+ in your preferred environment:

```powershell
python -m pip install -r requirements.txt
python scripts/prepare_data.py
python scripts/build_powerbi.py
python scripts/validate_report.py
```

The pipeline downloads approximately 249 MiB compressed, streams the wide source in chunks, and writes compact analytical facts. Allow roughly 400 MB for the dataset and curated files, plus Power BI cache and development tools. Internet access is required for the first download and first schema validation. Close Power BI before regenerating report files. Regeneration overwrites generated report definitions; retain UI edits separately or update the generator.

## Model and engineering

- Two fact tables: **DailyMeter** (540,570 customer-days) and **SystemInterval** (140,256 portfolio intervals).
- Shared Date dimension; Meter filters DailyMeter only; Hour filters SystemInterval only. One-to-many, single-direction relationships.
- Scenario and CarbonFactor are disconnected input tables.
- 25 explicit DAX measures with units, descriptions and display folders. Fact columns are hidden from report authors.
- Raw-to-curated energy reconciliation, nonnegative/finite value assertions, unique timestamps and expected row counts.
- Native visuals, consistent theme, explicit axes and scenario caveats, source-controlled report JSON.

Read [model and metric decisions](docs/MODEL.md), [DAX dictionary](docs/MEASURES.md), [case study](docs/CASE_STUDY.md).

## Scope boundaries

This is a local portfolio implementation, not a deployed production service. It has no live refresh, tenant deployment, production performance SLA or verified emissions inventory. Data is public and anonymized, so no artificial row-level security roles are included. Incremental refresh would belong in a later database-backed deployment; the static local CSV pipeline does not claim query folding.
