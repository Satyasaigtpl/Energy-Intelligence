"""Reproducible UCI electricity pipeline. Python 3.11+, pandas, numpy."""
from pathlib import Path
import hashlib, json, zipfile, urllib.request, calendar
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/electricity.zip'
OUT = ROOT / 'data/curated'
URL = 'https://archive.ics.uci.edu/static/public/321/electricityloaddiagrams20112014.zip'

def run():
    OUT.mkdir(parents=True, exist_ok=True)
    if not RAW.exists():
        RAW.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(URL, RAW)
    sha = hashlib.file_digest(RAW.open('rb'), 'sha256').hexdigest()
    daily, intervals = [], []
    source_rows = missing = negatives = zero = 0
    raw_sum = 0.0
    first_nonzero, last_nonzero = {}, {}
    dst = set()
    for y in range(2011, 2015):
        for m in (3, 10):
            day = max(w[calendar.SUNDAY] for w in calendar.monthcalendar(y, m))
            dst.add(f'{y}-{m:02}-{day:02}')
    with zipfile.ZipFile(RAW) as z:
        member = next(n for n in z.namelist() if n.endswith('LD2011_2014.txt') and not n.startswith('__MACOSX'))
        with z.open(member) as f:
            for part in pd.read_csv(f, sep=';', decimal=',', chunksize=96*31):
                labels = pd.to_datetime(part.iloc[:, 0])
                # Treat source timestamps as interval ends; keep original labels in interval fact.
                start = labels - pd.Timedelta(minutes=15)
                values = part.iloc[:, 1:].astype(float)
                arr = values.to_numpy()
                assert np.isfinite(arr).all(), 'Missing or non-finite readings'
                assert (arr >= 0).all(), 'Unexpected negative load'
                assert (labels.diff().dropna() == pd.Timedelta(minutes=15)).all()
                source_rows += len(part)
                missing += int(values.isna().sum().sum())
                negatives += int((arr < 0).sum())
                zero += int((arr == 0).sum())
                raw_sum += float(arr.sum() / 4)
                dates = start.dt.strftime('%Y-%m-%d').to_numpy()
                hours = start.dt.hour.to_numpy()
                transition = np.isin(dates, list(dst))
                system = arr.sum(axis=1)
                intervals.append(pd.DataFrame({'Timestamp': labels.dt.strftime('%Y-%m-%d %H:%M:%S'), 'Date': dates,
                    'Hour': hours, 'SystemKW': system, 'EnergyKWh': system/4,
                    'ValidPeakKW': np.where(transition, np.nan, system),
                    'DSTDay': transition.astype(int), 'ZeroReadings': (arr==0).sum(axis=1),
                    'PositiveMeters': (arr>0).sum(axis=1)}))
                for date in np.unique(dates):
                    mask = dates == date
                    a = arr[mask]
                    night = a[hours[mask] < 6].sum(axis=0)/4
                    daily.append(pd.DataFrame({'Date':date,'Meter':values.columns,'EnergyKWh':a.sum(axis=0)/4,
                        'NightKWh':night,'PeakKW':np.nan if date in dst else a.max(axis=0),
                        'Intervals':len(a),'ZeroReadings':(a==0).sum(axis=0)}))
                for j, meter in enumerate(values.columns):
                    nz = np.flatnonzero(arr[:,j] > 0)
                    if len(nz):
                        first_nonzero.setdefault(meter, dates[nz[0]])
                        last_nonzero[meter] = dates[nz[-1]]
                print(f'Processed {source_rows:,} intervals / {source_rows*370:,} readings', flush=True)
    fact = pd.concat(daily, ignore_index=True).groupby(['Date','Meter'],as_index=False).agg(
        EnergyKWh=('EnergyKWh','sum'),NightKWh=('NightKWh','sum'),PeakKW=('PeakKW','max'),
        Intervals=('Intervals','sum'),ZeroReadings=('ZeroReadings','sum'))
    fact['PreActivation'] = (fact.Date < fact.Meter.map(first_nonzero)).astype(int)
    interval = pd.concat(intervals,ignore_index=True)
    assert not interval.Timestamp.duplicated().any()
    assert len(interval)==140256 and len(fact)==1461*370
    assert np.isclose(fact.EnergyKWh.sum(),raw_sum,rtol=1e-10)
    assert np.isclose(interval.EnergyKWh.sum(),raw_sum,rtol=1e-10)
    assert (fact.Intervals==96).all()
    dates = pd.DataFrame({'Date':pd.date_range('2011-01-01','2014-12-31')})
    dates['Year']=dates.Date.dt.year
    dates['Month']=dates.Date.dt.strftime('%Y-%m')
    dates['MonthName']=dates.Date.dt.strftime('%b')
    dates['MonthNumber']=dates.Date.dt.month
    dates['Weekday']=dates.Date.dt.strftime('%a')
    dates['WeekdayNumber']=dates.Date.dt.dayofweek+1
    dates['DayType']=np.where(dates.WeekdayNumber>5,'Weekend','Weekday')
    dates['Date']=dates.Date.dt.strftime('%Y-%m-%d')
    dates['DSTDay']=dates.Date.isin(dst).astype(int)
    meters=pd.DataFrame({'Meter':sorted(first_nonzero)})
    meters['FirstPositiveDate']=meters.Meter.map(first_nonzero)
    meters['LastPositiveDate']=meters.Meter.map(last_nonzero)
    meters['Cohort']=meters.FirstPositiveDate.str[:4]
    totals=fact.groupby('Meter').EnergyKWh.sum()
    meters['PortfolioRank']=meters.Meter.map(totals.rank(ascending=False,method='first')).astype(int)
    meters['Group']=np.where(meters.PortfolioRank<=10,'Top 10 lifetime consumers','Other consumers')
    frames={'DailyMeter':fact,'SystemInterval':interval,'Date':dates,'Meter':meters,
        'Hour':pd.DataFrame({'Hour':range(24),'HourLabel':[f'{h:02}:00' for h in range(24)]}),
        'Scenario':pd.DataFrame({'Scenario':['Conservative','Planning','Ambitious'],'Reduction':[.05,.1,.2]}),
        'CarbonFactor':pd.DataFrame({'Factor':[.1,.2,.3,.4,.5,.6]})}
    for name,frame in frames.items():
        frame.to_csv(OUT/f'{name}.csv',index=False,float_format='%.9f')
    annual=fact.groupby(fact.Date.str[:4]).EnergyKWh.sum()
    peak=interval.loc[interval.ValidPeakKW.idxmax()]
    audit={'source':URL,'license':'CC BY 4.0','attribution':'Trindade, A. (2015). ElectricityLoadDiagrams20112014. UCI. doi:10.24432/C58C86',
        'sha256':sha,'source_intervals':source_rows,'meters':370,'source_readings':source_rows*370,
        'missing':missing,'negative':negatives,'zero_readings':zero,'energy_kwh':raw_sum,
        'annual_kwh':annual.to_dict(),'peak_kw_excluding_dst_days':float(peak.ValidPeakKW),
        'peak_timestamp_original_label':peak.Timestamp,'top_10_energy_share':float(totals.nlargest(10).sum()/raw_sum),
        'night_energy_share':float(fact.NightKWh.sum()/raw_sum),'dst_dates':sorted(dst),
        'rows':{k:len(v) for k,v in frames.items()},'checks':'PASS: row counts, finite nonnegative values, timestamp uniqueness, 96 intervals/day/meter, energy reconciliation'}
    (ROOT/'qa/data-audit.json').write_text(json.dumps(audit,indent=2))
    print(json.dumps(audit,indent=2),flush=True)

if __name__=='__main__':
    run()
