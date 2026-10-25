# Copyright (c) 2026 the repository owner. All rights reserved. See LICENSE.
"""Optional observed-data context. Never estimates behavioural parameters.

FRED public CSV downloads returned HTTP 404 during development. The refresh
adapter therefore reads the five observations displayed on official series
pages, checks the format and units, and retains the old snapshot on failure.
This is a latest-vintage context panel, not a historical API or backtest feed.
"""
import csv
import datetime as dt
import html
import io
import json
import math
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SERIES = {
    'GDP':('Nominal GDP','USD billion SAAR','Quarterly'),
    'GCE':('Government purchases, including investment','USD billion SAAR','Quarterly'),
    'GPDI':('Private domestic investment','USD billion SAAR','Quarterly'),
    'NETEXP':('Net exports','USD billion SAAR','Quarterly'),
    'GDPDEF':('GDP price deflator','2017 = 100','Quarterly'),
    'CPATAX':('Corporate profits after tax, IVA and CCAdj','USD billion SAAR','Quarterly'),
    'POPTHM':('Population','thousand persons','Monthly'),
    'GS10':('10-year Treasury yield','percent','Monthly'),
}


def period_date(s):
    s=s.strip().rstrip(':').strip()
    q=re.fullmatch(r'Q([1-4]) (\d{4})',s)
    if q:return f'{q[2]}-{1+(int(q[1])-1)*3:02d}-01'
    try:return dt.datetime.strptime(s,'%b %Y').date().isoformat()
    except ValueError:raise ValueError('Unknown FRED observation period: '+s)


def fetch_series(key):
    if key not in SERIES:raise ValueError('Unknown series.')
    url='https://fred.stlouisfed.org/series/'+key
    with urllib.request.urlopen(url,timeout=10) as response:
        s=response.read(2_000_000).decode('utf-8')
    pattern=r'<td[^>]*>\s*(Q[1-4] \d{4}|[A-Z][a-z]{2} \d{4}):(?:&nbsp;|\s)*</td>\s*<td[^>]*class="series-obs value"[^>]*>\s*([-\d,.]+)\s*</td>'
    observations=[]
    for period,value in re.findall(pattern,s):
        observations.append(dict(date=period_date(period),period=period,value=float(value.replace(',',''))))
    if len(observations)<2 or not all(math.isfinite(x['value']) for x in observations):
        raise ValueError(key+': FRED page format changed or observations are missing.')
    unit_tokens={'GDP':'Billions of Dollars','GCE':'Billions of Dollars','GPDI':'Billions of Dollars',
                 'NETEXP':'Billions of Dollars','GDPDEF':'Index 2017=100','CPATAX':'Billions of Dollars',
                 'POPTHM':'Thousands','GS10':'Percent'}
    if unit_tokens[key] not in html.unescape(s):
        raise ValueError(key+': expected units could not be verified.')
    return dict(series_id=key,name=SERIES[key][0],units=SERIES[key][1],frequency=SERIES[key][2],
                url=url,observations=observations,method='Official FRED page: displayed observations')


def refresh(destination):
    with ThreadPoolExecutor(max_workers=4) as pool:
        records=list(pool.map(fetch_series,SERIES))
    result=dict(retrieved_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                vintage='Latest revised observations; not a point-in-time vintage',
                coverage='United States; a small context snapshot, not a fitted model',series=records)
    result['anchors']=anchors(result)
    path=Path(destination)
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(result,indent=2))
    temporary.replace(path)
    return result


def anchors(snapshot):
    series={s['series_id']:s for s in snapshot.get('series',[])}
    needed=['GDP','GCE','GPDI','NETEXP']
    if not all(k in series for k in needed):return {}
    obs={k:{x['date']:x['value'] for x in series[k]['observations']} for k in needed}
    common=set(obs['GDP'])
    for k in needed:common &= set(obs[k])
    if not common:return {}
    date=max(common); gdp=obs['GDP'][date]
    if gdp<=0:raise ValueError('GDP must be positive.')
    return dict(period=date,government_share=obs['GCE'][date]/gdp,
                investment_share=obs['GPDI'][date]/gdp,net_export_share=obs['NETEXP'][date]/gdp,
                note='Same-quarter nominal expenditure ratios. No annualisation multiplication is needed: all four flows are SAAR. These are suggested opening anchors only. Consumption, household split, stocks and behavioural coefficients remain assumptions.')


def parse_csv(text):
    """Strict quarterly context import; amounts USD bn SAAR, not raw quarterly totals."""
    reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    if len(reader.fieldnames or []) != len(set(reader.fieldnames or [])):
        raise ValueError('Duplicate CSV column names are not accepted.')
    required={'date','GDP','GCE','GPDI','NETEXP'}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError('CSV requires date,GDP,GCE,GPDI,NETEXP. Nominal flows must all be USD billion SAAR; date must be a quarter start.')
    allowed=required|{'GDPDEF','CPATAX'}
    if set(reader.fieldnames)-allowed:raise ValueError('Unknown CSV columns. Download the template for supported fields.')
    rows=list(reader)
    if not rows or len(rows)>500:raise ValueError('Import between 1 and 500 quarterly observations.')
    seen=set(); records={k:[] for k in reader.fieldnames if k!='date'}
    for row in rows:
        date=dt.date.fromisoformat(row['date'])
        if date.month not in (1,4,7,10) or date.day!=1:raise ValueError('Use quarter-start dates: January, April, July or October 1.')
        if date in seen:raise ValueError('Duplicate quarter in CSV.')
        seen.add(date)
        for key in records:
            value=float(row[key])
            if not math.isfinite(value):raise ValueError('Every value must be finite; missing observations are not filled.')
            if key not in ('NETEXP','CPATAX') and value<=0:raise ValueError(key+' must be positive.')
            records[key].append(dict(date=date.isoformat(),period=f'Q{(date.month-1)//3+1} {date.year}',value=value))
    data=dict(retrieved_at=None,vintage='User-supplied CSV; release vintage and source not verified',
              coverage='User import declared as US quarterly USD billion SAAR',
              series=[dict(series_id=k,name=SERIES[k][0],units=SERIES[k][1],frequency='Quarterly',url=None,
                           observations=sorted(v,key=lambda x:x['date'],reverse=True),method='User CSV') for k,v in records.items()])
    data['anchors']=anchors(data)
    return data
