# Portfolio case study — Energy Intelligence

## Problem

An energy services team needs a defensible view of customer consumption, portfolio demand and hypothetical reduction opportunities. Raw quarter-hour readings are too detailed for an executive report, and common shortcuts can misstate energy, demand and emissions.

## Approach

Process the complete UCI dataset: 370 customers × 140,256 timestamps = **51,894,720 readings**. Convert kW readings into quarter-hour kWh, preserve zeros, and retain source lineage with a SHA-256 checksum. Build two complementary facts: customer-day energy for account analysis and simultaneous portfolio intervals for demand. Use Power BI dimensions and explicit measures to keep their filter behavior understandable.

## Findings from the data

All-period results, except where stated:

| Finding | Evidence | Decision implication |
|---|---|---|
| Customer concentration is high | Top 10 customers account for **52.54%** of energy | Start account-level investigation with the largest consumers; do not assume consumption implies inefficiency |
| Demand has a strong intraday shape | Highest average interval-start hour is **18:00**, approximately **259.41 MW**, excluding DST dates | Investigate whether any large loads are flexible during late-afternoon/early-evening hours |
| Coincident peak is materially above average | **452.65 MW** peak vs **195.67 MW** average; **43.23%** load factor | Assess the timing of high loads; this is not a measure of equipment efficiency |
| Recorded 2014 energy was nearly flat against 2013 | **1,965.84 GWh**, approximately **+0.75%** YoY | Examine stable customer cohorts and weather before claiming efficiency improvement |
| Zeros need interpretation | **20.15%** zero readings; **19.19%** of readings occur on dates before first positive consumption | Blindly replacing zeros would distort the source and onboarding behavior |
| Night consumption is substantial | **14.51%** of energy in interval-start hours 00:00–05:59 | Use as a screening signal only; operational schedules are unknown |

Source-label timestamp of the non-DST portfolio peak: **2013-07-09 17:00:00**, corresponding to assumed interval start 16:45. The historical four-year total is **6,857.01 GWh**. These figures describe this anonymized customer portfolio, not Portugal's national electricity system.

## Scenario example

At the default assumed 0.30 kg CO2e/kWh, the four-year illustrative footprint is approximately **2,057,103 tCO2e**. A uniform 10% reduction would correspond to approximately **685,701 MWh** and **205,710 tCO2e** avoided under that assumption. These are modeled possibilities, not measured emissions or realized savings.

## Portfolio demonstration

1. Open the consumption page and select 2014. Explain the 1,965.84 GWh total and roughly 0.8% rounded growth.
2. Filter a first-positive-year cohort and explain why onboarding affects comparisons.
3. Open demand and explain why 452.65 MW is calculated from simultaneous readings.
4. Change the carbon factor and reduction scenario; describe the assumptions and limitations.
5. Open quality and show zero rates, inferred onboarding and the reconciled energy totals.

## Resume wording

“Built a Power BI electricity analytics portfolio using 51.9 million public meter readings; engineered two analytical fact tables, 25 documented DAX measures and four interactive report pages, with source checksums, energy reconciliation and explicit carbon-scenario assumptions.”

Do not claim realized financial savings, production deployment, verified emissions reductions or a national grid study.
