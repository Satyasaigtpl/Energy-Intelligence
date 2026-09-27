"""Generate a native PBIP / PBIR report and Import semantic model."""
from pathlib import Path
import json, uuid

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'Energy Intelligence'
REPORT=PROJECT/'Energy Intelligence.Report'
MODEL=PROJECT/'Energy Intelligence.SemanticModel'
BASE='https://developer.microsoft.com/json-schemas/fabric/item/report/definition/'

def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2),encoding='utf-8')

def lit(v):
    value=('true' if v else 'false') if isinstance(v,bool) else (str(v)+'D' if isinstance(v,(int,float)) else "'"+v.replace("'","''")+"'")
    return {'expr':{'Literal':{'Value':value}}}
def color(v): return {'solid':{'color':lit(v)}}
def obj(**p): return [{'properties':p}]

TABLES={
 'Date':{'Date':'date','Year':'int64','Month':'string','MonthName':'string','MonthNumber':'int64','Weekday':'string','WeekdayNumber':'int64','DayType':'string','DSTDay':'int64'},
 'Meter':{'Meter':'string','FirstPositiveDate':'date','LastPositiveDate':'date','Cohort':'string','PortfolioRank':'int64','Group':'string'},
 'Hour':{'Hour':'int64','HourLabel':'string'},
 'DailyMeter':{'Date':'date','Meter':'string','EnergyKWh':'double','NightKWh':'double','PeakKW':'double','Intervals':'int64','ZeroReadings':'int64','PreActivation':'int64'},
 'SystemInterval':{'Timestamp':'dateTime','Date':'date','Hour':'int64','SystemKW':'double','EnergyKWh':'double','ValidPeakKW':'double','DSTDay':'int64','ZeroReadings':'int64','PositiveMeters':'int64'},
 'Scenario':{'Scenario':'string','Reduction':'double'},
 'CarbonFactor':{'Factor':'double'}
}
# Name, DAX, format, display folder, business definition.
MEASURES=[
 ('Energy MWh','DIVIDE(SUM(DailyMeter[EnergyKWh]),1000)','#,0.0','Consumption','Metered energy, source kW divided by four and summed.'),
 ('Energy GWh','DIVIDE([Energy MWh],1000)','#,0.00','Consumption','Metered energy in GWh.'),
 ('Night Share','DIVIDE(SUM(DailyMeter[NightKWh]),SUM(DailyMeter[EnergyKWh]))','0.0%','Consumption','Energy during assumed interval starts 00:00 through 05:45 / all energy. Not a waste estimate.'),
 ('Meters with Usage','CALCULATE(DISTINCTCOUNT(DailyMeter[Meter]),DailyMeter[EnergyKWh]>0)','#,0','Consumption','Meters with positive energy in the current selection.'),
 ('Energy PY MWh','CALCULATE([Energy MWh],DATEADD(\'Date\'[Date],-1,YEAR))','#,0.0','Consumption','Same selected calendar dates one year earlier.'),
 ('Energy YoY','IF(HASONEVALUE(\'Date\'[Year]),DIVIDE([Energy MWh]-[Energy PY MWh],[Energy PY MWh]))','0.0%;-0.0%;0.0%','Consumption','Calendar comparison; cohort expansion can affect growth. Blank unless one year is selected and prior-year data exists.'),
 ('Meter Rank','RANKX(ALLSELECTED(Meter[Meter]),[Energy MWh],,DESC,Dense)','#,0','Consumption','Consumption rank in current selected meter population.'),
 ('System Peak MW','DIVIDE(MAX(SystemInterval[ValidPeakKW]),1000)','#,0.00','Demand','Coincident portfolio peak, excludes entire DST transition days. No meter filtering.'),
 ('System Average MW','DIVIDE(CALCULATE(AVERAGE(SystemInterval[SystemKW]),SystemInterval[DSTDay]=0),1000)','#,0.00','Demand','Average portfolio load excluding DST transition days.'),
 ('System Load Factor','DIVIDE([System Average MW],[System Peak MW])','0.0%','Demand','Mean / peak for same selected valid intervals, not sum of meter peaks.'),
 ('System Energy MWh','DIVIDE(SUM(SystemInterval[EnergyKWh]),1000)','#,0.0','Demand','Portfolio energy; independent of meter filters.'),
 ('Valid Intervals','CALCULATE(COUNTROWS(SystemInterval),SystemInterval[DSTDay]=0)','#,0','Demand','15-minute portfolio intervals outside DST transition days.'),
 ('Reduction Selected','SELECTEDVALUE(Scenario[Reduction],0.1)','0%','Scenario','Default 10% when no single scenario is selected.'),
 ('Carbon Factor Selected','SELECTEDVALUE(CarbonFactor[Factor],0.3)','0.00','Scenario','Illustrative kg CO2e/kWh; default 0.30. Not an observed grid factor.'),
 ('Scenario Baseline tCO2e','[Energy MWh]*[Carbon Factor Selected]','#,0.0','Scenario','Illustrative footprint using a constant assumed factor, not a verified inventory.'),
 ('Scenario Avoided tCO2e','[Scenario Baseline tCO2e]*[Reduction Selected]','#,0.0','Scenario','Assumes proportional demand reduction at unchanged carbon intensity.'),
 ('Scenario Remaining tCO2e','[Scenario Baseline tCO2e]-[Scenario Avoided tCO2e]','#,0.0','Scenario','Scenario baseline less hypothetical avoided emissions.'),
 ('Scenario Saved MWh','[Energy MWh]*[Reduction Selected]','#,0.0','Scenario','Hypothetical reduction in measured consumption, not achieved savings.'),
 ('Readings','SUM(DailyMeter[Intervals])','#,0','Quality','Count of customer-interval readings including zero values.'),
 ('Readings Million','DIVIDE([Readings],1000000)','0.00','Quality','Source customer readings expressed in millions.'),
 ('Zero Share','DIVIDE(SUM(DailyMeter[ZeroReadings]),[Readings])','0.0%','Quality','All zero readings; includes onboarding and DST handling, not a missing-data rate.'),
 ('Pre-activation Share','DIVIDE(CALCULATE(SUM(DailyMeter[Intervals]),DailyMeter[PreActivation]=1),[Readings])','0.0%','Quality','Readings on dates before the first positive date. Inferred onboarding, not confirmed metadata.'),
 ('DST Days','CALCULATE(COUNTROWS(\'Date\'),\'Date\'[DSTDay]=1)','#,0','Quality','European clock-change dates, excluded from peak/load-factor metrics.'),
 ('Energy Reconciliation kWh','ROUND(SUM(SystemInterval[EnergyKWh])-CALCULATE(SUM(DailyMeter[EnergyKWh]),REMOVEFILTERS(Meter)),3)','0.000','Quality','System energy minus meter energy rounded to 0.001 kWh to remove floating-point noise; use with date filters only.'),
 ('Coverage Days','DISTINCTCOUNT(DailyMeter[Date])','#,0','Quality','Calendar dates represented in the meter fact.')
]

def model():
    tables=[]
    for name,cols in TABLES.items():
        columns=[]
        for col,typ in cols.items():
            c={'name':col,'dataType':'dateTime' if typ=='date' else typ,'sourceColumn':col,'summarizeBy':'none'}
            if typ in ('date','dateTime'): c['formatString']='yyyy-MM-dd' if typ=='date' else 'yyyy-MM-dd HH:mm'
            if name in ('DailyMeter','SystemInterval'): c['isHidden']=True
            if (name,col)==('Date','Date'): c['isKey']=True
            if (name,col) in [('Date','MonthName'),('Date','Weekday'),('Hour','HourLabel')]: c['sortByColumn']={'MonthName':'MonthNumber','Weekday':'WeekdayNumber','HourLabel':'Hour'}[col]
            if name=='Scenario' and col=='Reduction': c['formatString']='0%'
            if name=='CarbonFactor': c['formatString']='0.00'
            columns.append(c)
        mtypes={'date':'type date','dateTime':'type datetime','string':'type text','double':'type number','int64':'Int64.Type'}
        pairs=', '.join('{"'+c+'", '+mtypes[t]+'}' for c,t in cols.items())
        expr=['let',f'    Source = Csv.Document(File.Contents(DataFolder & "{name}.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),','    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',f'    Typed = Table.TransformColumnTypes(Headers, {{{pairs}}}, "en-US")','in','    Typed']
        table={'name':name,'columns':columns,'partitions':[{'name':name,'mode':'import','source':{'type':'m','expression':expr}}]}
        if name=='Date': table['dataCategory']='Time'
        tables.append(table)
    tables.append({'name':'Metrics','columns':[{'name':'Label','dataType':'string','sourceColumn':'Label','isHidden':True}],
        'partitions':[{'name':'Metrics','mode':'import','source':{'type':'m','expression':'#table(type table [Label = text], {{"Energy Intelligence"}})'}}],
        'measures':[{'name':n,'expression':e,'formatString':f,'displayFolder':g,'description':d} for n,e,f,g,d in MEASURES]})
    rel=[]
    for ft,fc,tt,tc in [('DailyMeter','Date','Date','Date'),('DailyMeter','Meter','Meter','Meter'),('SystemInterval','Date','Date','Date'),('SystemInterval','Hour','Hour','Hour')]:
        rel.append({'name':str(uuid.uuid5(uuid.NAMESPACE_DNS,ft+fc+tt+tc)),'fromTable':ft,'fromColumn':fc,'toTable':tt,'toColumn':tc,'crossFilteringBehavior':'oneDirection'})
    save(MODEL/'definition.pbism',{'version':'1.0','settings':{}})
    save(MODEL/'model.bim',{'name':'Energy Intelligence','compatibilityLevel':1600,'model':{'culture':'en-US','defaultPowerBIDataSourceVersion':'powerBI_V3','sourceQueryCulture':'en-US','tables':tables,'relationships':rel,'expressions':[{'name':'DataFolder','kind':'m','expression':'"'+str(ROOT/'data/curated').replace('\\','/')+'/" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'}],'annotations':[{'name':'__PBI_TimeIntelligenceEnabled','value':'0'}]}})
    (ROOT/'docs/MEASURES.md').write_text('# Measure dictionary\n\n'+ '\n\n'.join(f'### {n}\n{d}\n```dax\n{e}\n```' for n,e,f,g,d in MEASURES),encoding='utf-8')

def field(table,col,measure=False):
    return {('Measure' if measure else 'Column'):{'Expression':{'SourceRef':{'Entity':table}},'Property':col}}
def projection(table,col,measure=False):
    return {'field':field(table,col,measure),'queryRef':table+'.'+col,'nativeQueryRef':col}

PAGE=None
COUNT=0
INK='#183C38'; TEAL='#087F72'; MUTED='#617773'; BG='#F0F4F1'; GOLD='#BA8131'
def visual(kind,title,x,y,w,h,roles=None,objects=None,sort=None,bg='#FFFFFF'):
    global COUNT
    COUNT+=1
    v={'visualType':kind,'visualContainerObjects':{'title':obj(show=lit(bool(title)),text=lit(title),fontSize=lit(12),fontColor=color(INK),fontFamily=lit('Segoe UI Semibold')),'background':obj(show=lit(True),color=color(bg),transparency=lit(0)),'border':obj(show=lit(False)),'visualHeader':obj(show=lit(False))}}
    if roles:
        v['query']={'queryState':{r:{'projections':ps} for r,ps in roles.items()}}
        if sort: v['query']['sortDefinition']={'sort':[{'field':sort[0],'direction':sort[1]}],'isDefaultSort':False}
    if objects: v['objects']=objects
    name=f'v{COUNT:03}'
    save(PAGE/'visuals'/name/'visual.json',{'$schema':BASE+'visualContainer/2.1.0/schema.json','name':name,'position':{'x':x,'y':y,'width':w,'height':h,'z':COUNT,'tabOrder':COUNT},'visual':v})
    return name
def text(txt,x,y,w,h,size=14,fg=INK,bg=BG,bold=False):
    name=visual('textbox','',x,y,w,max(h,size*1.5+23),objects={'general':obj(paragraphs=[{'textRuns':[{'value':txt,'textStyle':{'fontFamily':'Segoe UI','fontSize':str(size)+'pt','color':fg,'fontWeight':'bold' if bold else 'normal'}}]}])},bg=bg)
    path=PAGE/'visuals'/name/'visual.json'
    definition=json.loads(path.read_text())
    definition['visual']['visualContainerObjects']['padding']=obj(top=lit(0),bottom=lit(0),left=lit(0),right=lit(0))
    save(path,definition)
    return name
def card(name,label,x,y,w=290):
    precision=0 if name in ['Meters with Usage','Valid Intervals'] else 3 if name=='Energy Reconciliation kWh' else 2 if name in ['Readings Million','Energy GWh','System Peak MW','System Average MW'] else 1
    return visual('card',label,x,y,w,102,{'Values':[projection('Metrics',name,True)]},{'labels':obj(color=color(TEAL),fontSize=lit(29),labelDisplayUnits=lit(1),labelPrecision=lit(precision)),'categoryLabels':obj(show=lit(False))})
def chart(kind,title,x,y,w,h,table,col,measures):
    return visual(kind,title,x,y,w,h,{'Category':[projection(table,col)],'Y':[projection('Metrics',m,True) for m in measures]},
        {'dataPoint':obj(defaultColor=color(TEAL)),'categoryAxis':obj(labelColor=color(MUTED),fontSize=lit(10),showAxisTitle=lit(False),minimumCategoryWidth=lit(10)),'valueAxis':obj(labelColor=color(MUTED),fontSize=lit(10),showAxisTitle=lit(False)),'legend':obj(show=lit(len(measures)>1))},(field(table,col),'Ascending'))
def slicer(table,col,label,x,y,w=190):
    return visual('slicer',label,x,y,w,72,{'Values':[projection(table,col)]},{'data':obj(mode=lit('Dropdown')),'header':obj(show=lit(False)),'selection':obj(singleSelect=lit(table in ['Scenario','CarbonFactor']))})
def page(name,title,subtitle,index):
    global PAGE
    PAGE=REPORT/'definition/pages'/name
    save(PAGE/'page.json',{'$schema':BASE+'page/1.0.0/schema.json','name':name,'displayName':title,'displayOption':'FitToPage','height':800,'width':1440,'objects':{'background':obj(color=color(BG),transparency=lit(0))}})
    text('FIELDNOTES  /  ENERGY INTELLIGENCE',28,10,1000,38,11,TEAL,bold=True)
    text(title,28,47,1230,60,28,bold=True)
    text(subtitle,30,101,1375,43,11,MUTED)
    text(f'0{index} / 04',1290,48,120,39,18,TEAL)
    text('PORTUGAL  |  2011–2014  •  UCI / Artur Trindade  •  Historical portfolio study',30,759,1250,38,9,MUTED)
    slicer('Date','Year','YEAR',30,151)

def report():
    save(PROJECT/'Energy Intelligence.pbip',{'version':'1.0','artifacts':[{'report':{'path':'Energy Intelligence.Report'}}],'settings':{'enableAutoRecovery':True}})
    save(REPORT/'definition.pbir',{'version':'4.0','datasetReference':{'byPath':{'path':'../Energy Intelligence.SemanticModel'}}})
    save(REPORT/'definition/version.json',{'$schema':BASE+'versionMetadata/1.0.0/schema.json','version':'2.0.0'})
    theme={'name':'Fieldnotes Energy','dataColors':[TEAL,GOLD,'#6EA79A','#254F69','#91A378','#CA6F54'],'background':BG,'foreground':INK,'tableAccent':TEAL,'textClasses':{'title':{'fontFace':'Segoe UI Semibold','color':INK},'label':{'fontFace':'Segoe UI','color':MUTED}}}
    save(REPORT/'StaticResources/RegisteredResources/Fieldnotes.json',theme)
    save(ROOT/'docs/Fieldnotes-theme.json',theme)
    save(REPORT/'definition/report.json',{'$schema':BASE+'report/2.0.0/schema.json','themeCollection':{'customTheme':{'name':'Fieldnotes','reportVersionAtImport':'5.55','type':'RegisteredResources'}},'resourcePackages':[{'name':'RegisteredResources','type':'RegisteredResources','items':[{'name':'Fieldnotes','path':'Fieldnotes.json','type':'CustomTheme'}]}],'objects':{'outspacePane':obj(expanded=lit(False))}})
    pages=['overview','demand','carbon','quality']
    save(REPORT/'definition/pages/pages.json',{'$schema':BASE+'pagesMetadata/1.0.0/schema.json','pageOrder':pages,'activePageName':'overview'})

    page('overview','Consumption & customer portfolio','Where is electricity being used, and which customer groups deserve a closer look?',1)
    slicer('Meter','Cohort','FIRST POSITIVE YEAR',240,151,250)
    slicer('Meter','Meter','CUSTOMER',510,151,250)
    text('Explore a year, cohort or customer. Click a chart to cross-filter.',790,167,605,46,12,MUTED)
    for i,(m,l) in enumerate([('Energy GWh','METERED ENERGY · GWh'),('Meters with Usage','CUSTOMERS WITH USAGE'),('Night Share','00:00–06:00 ENERGY SHARE'),('Energy YoY','YoY · SELECT ONE YEAR')]):card(m,l,30+i*350,237,330)
    chart('lineChart','Monthly electricity consumption · MWh',30,359,835,285,'Date','Month',['Energy MWh'])
    chart('clusteredColumnChart','Consumption by onboarding cohort · MWh',885,359,525,285,'Meter','Cohort',['Energy MWh'])
    text('READ THIS CORRECTLY',45,663,270,25,11,TEAL,bold=True)
    text('Growth includes customers joining the dataset. Filter a cohort before comparing years. Night use can be legitimate; it is a screening signal, not proven waste.',45,696,1330,55,13)

    page('demand','Peak demand & load performance','Identify when the portfolio is under the most pressure. All demand measures cover the full customer portfolio.',2)
    slicer('Date','Month','MONTH',240,151,250)
    slicer('Date','DayType','DAY TYPE',510,151,250)
    text('Peak metrics exclude 8 clock-change days; energy retains them.',790,167,605,46,12,MUTED)
    for i,(m,l) in enumerate([('System Peak MW','COINCIDENT PEAK · MW'),('System Average MW','MEAN DEMAND · MW'),('System Load Factor','PORTFOLIO LOAD FACTOR'),('Valid Intervals','VALID 15-MINUTE INTERVALS')]):card(m,l,30+i*350,237,330)
    chart('lineChart','Average demand by hour · MW | clock-change days excluded',30,359,835,285,'Hour','HourLabel',['System Average MW'])
    chart('clusteredColumnChart','Monthly coincident peak · MW',885,359,525,285,'Date','Month',['System Peak MW'])
    text('OPERATIONAL DECISION',45,663,330,25,11,TEAL,bold=True)
    text('Use high-demand hours to investigate flexible loads. A peak is the maximum simultaneous portfolio demand; customer peaks must never be added together.',45,696,1320,55,13)

    page('carbon','Efficiency & carbon scenarios','An interactive planning exercise using measured energy and explicitly assumed emissions factors.',3)
    slicer('Scenario','Scenario','REDUCTION SCENARIO',240,151,250)
    slicer('CarbonFactor','Factor','FACTOR · kg CO2e / kWh',510,151,250)
    text('Defaults: 10% reduction · 0.30 kg CO2e/kWh. Assumptions, not actuals.',790,167,605,46,12,GOLD)
    for i,(m,l) in enumerate([('Scenario Baseline tCO2e','ILLUSTRATIVE BASELINE · tCO2e'),('Scenario Avoided tCO2e','POTENTIAL AVOIDED · tCO2e'),('Scenario Saved MWh','POTENTIAL ENERGY SAVED · MWh'),('Reduction Selected','SELECTED REDUCTION')]):card(m,l,30+i*350,237,330)
    chart('lineChart','Monthly footprint scenario · tCO2e',30,359,835,285,'Date','Month',['Scenario Baseline tCO2e','Scenario Remaining tCO2e'])
    chart('clusteredColumnChart','Potential reduction by scenario · tCO2e',885,359,525,285,'Scenario','Scenario',['Scenario Avoided tCO2e'])
    text('PLANNING BOUNDARY',45,663,330,25,11,GOLD,bold=True)
    text('No measured emissions or verified savings are available. This assumes uniform energy reduction and constant intensity; load shifting alone does not guarantee carbon savings.',45,696,1320,55,13)

    page('quality','Data quality & interpretation','Make the limitations visible before turning readings into a business recommendation.',4)
    text('Full portfolio quality checks. Use year selection to inspect changing coverage.',250,166,1120,48,12,MUTED)
    for i,(m,l) in enumerate([('Readings Million','SOURCE READINGS · MILLION'),('Zero Share','ZERO READINGS'),('Pre-activation Share','BEFORE FIRST POSITIVE DATE'),('Energy Reconciliation kWh','ENERGY RECONCILIATION · kWh')]):card(m,l,30+i*350,237,330)
    chart('clusteredColumnChart','Zero-reading share by year',30,359,650,270,'Date','Year',['Zero Share'])
    text('MODEL CONTRACT',725,366,640,34,16,TEAL,bold=True,bg='#FFFFFF')
    text('• One customer-day per row in the consumption fact.\n• One portfolio interval per row in the demand fact.\n• kWh = source kW / 4. No zero-value imputation.\n• Dates use interval end minus 15 minutes (assumption).\n• Source DST conventions are preserved in energy.\n• Meter filters apply only to customer consumption.',725,411,650,218,14,bg='#FFFFFF')
    text('AUDITABLE BY DESIGN',45,657,330,28,11,TEAL,bold=True)
    text('Open qa/data-audit.json for checksum, row counts and reconciliations. Historical anonymized customers have no site, sector, tariff or emissions metadata.',45,694,1320,59,13)

if __name__=='__main__':
    model(); report(); print(f'Created native Power BI project with {COUNT} visuals and {len(MEASURES)} measures: {PROJECT}')
