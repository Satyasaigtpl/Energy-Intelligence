# Measure dictionary

### Energy MWh
Metered energy, source kW divided by four and summed.
```dax
DIVIDE(SUM(DailyMeter[EnergyKWh]),1000)
```

### Energy GWh
Metered energy in GWh.
```dax
DIVIDE([Energy MWh],1000)
```

### Night Share
Energy during assumed interval starts 00:00 through 05:45 / all energy. Not a waste estimate.
```dax
DIVIDE(SUM(DailyMeter[NightKWh]),SUM(DailyMeter[EnergyKWh]))
```

### Meters with Usage
Meters with positive energy in the current selection.
```dax
CALCULATE(DISTINCTCOUNT(DailyMeter[Meter]),DailyMeter[EnergyKWh]>0)
```

### Energy PY MWh
Same selected calendar dates one year earlier.
```dax
CALCULATE([Energy MWh],DATEADD('Date'[Date],-1,YEAR))
```

### Energy YoY
Calendar comparison; cohort expansion can affect growth. Blank unless one year is selected and prior-year data exists.
```dax
IF(HASONEVALUE('Date'[Year]),DIVIDE([Energy MWh]-[Energy PY MWh],[Energy PY MWh]))
```

### Meter Rank
Consumption rank in current selected meter population.
```dax
RANKX(ALLSELECTED(Meter[Meter]),[Energy MWh],,DESC,Dense)
```

### System Peak MW
Coincident portfolio peak, excludes entire DST transition days. No meter filtering.
```dax
DIVIDE(MAX(SystemInterval[ValidPeakKW]),1000)
```

### System Average MW
Average portfolio load excluding DST transition days.
```dax
DIVIDE(CALCULATE(AVERAGE(SystemInterval[SystemKW]),SystemInterval[DSTDay]=0),1000)
```

### System Load Factor
Mean / peak for same selected valid intervals, not sum of meter peaks.
```dax
DIVIDE([System Average MW],[System Peak MW])
```

### System Energy MWh
Portfolio energy; independent of meter filters.
```dax
DIVIDE(SUM(SystemInterval[EnergyKWh]),1000)
```

### Valid Intervals
15-minute portfolio intervals outside DST transition days.
```dax
CALCULATE(COUNTROWS(SystemInterval),SystemInterval[DSTDay]=0)
```

### Reduction Selected
Default 10% when no single scenario is selected.
```dax
SELECTEDVALUE(Scenario[Reduction],0.1)
```

### Carbon Factor Selected
Illustrative kg CO2e/kWh; default 0.30. Not an observed grid factor.
```dax
SELECTEDVALUE(CarbonFactor[Factor],0.3)
```

### Scenario Baseline tCO2e
Illustrative footprint using a constant assumed factor, not a verified inventory.
```dax
[Energy MWh]*[Carbon Factor Selected]
```

### Scenario Avoided tCO2e
Assumes proportional demand reduction at unchanged carbon intensity.
```dax
[Scenario Baseline tCO2e]*[Reduction Selected]
```

### Scenario Remaining tCO2e
Scenario baseline less hypothetical avoided emissions.
```dax
[Scenario Baseline tCO2e]-[Scenario Avoided tCO2e]
```

### Scenario Saved MWh
Hypothetical reduction in measured consumption, not achieved savings.
```dax
[Energy MWh]*[Reduction Selected]
```

### Readings
Count of customer-interval readings including zero values.
```dax
SUM(DailyMeter[Intervals])
```

### Readings Million
Source customer readings expressed in millions.
```dax
DIVIDE([Readings],1000000)
```

### Zero Share
All zero readings; includes onboarding and DST handling, not a missing-data rate.
```dax
DIVIDE(SUM(DailyMeter[ZeroReadings]),[Readings])
```

### Pre-activation Share
Readings on dates before the first positive date. Inferred onboarding, not confirmed metadata.
```dax
DIVIDE(CALCULATE(SUM(DailyMeter[Intervals]),DailyMeter[PreActivation]=1),[Readings])
```

### DST Days
European clock-change dates, excluded from peak/load-factor metrics.
```dax
CALCULATE(COUNTROWS('Date'),'Date'[DSTDay]=1)
```

### Energy Reconciliation kWh
System energy minus meter energy rounded to 0.001 kWh to remove floating-point noise; use with date filters only.
```dax
ROUND(SUM(SystemInterval[EnergyKWh])-CALCULATE(SUM(DailyMeter[EnergyKWh]),REMOVEFILTERS(Meter)),3)
```

### Coverage Days
Calendar dates represented in the meter fact.
```dax
DISTINCTCOUNT(DailyMeter[Date])
```