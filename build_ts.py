"""Build ts.json: stop and search counts by year, area and ethnic group,
with census denominators on four bases (2011/2021 x all ages/10-34 x both/male)."""
import pandas as pd, json, warnings
warnings.filterwarnings('ignore')

SEARCH = '/mnt/user-data/uploads/stop-and-search-2006-2023.csv'
CENSUS = '/mnt/user-data/outputs/census_2011_2021_tidy.csv'

# search-file ethnicity -> census detailed group
M = {'White British':'English, Welsh, Scottish, Northern Irish or British','White Irish':'Irish',
 'Gypsy or Irish Traveller':'Gypsy or Irish Traveller','Roma':'Roma',
 'Any Other White Background':'Other White','Indian':'Indian','Pakistani':'Pakistani',
 'Bangladeshi':'Bangladeshi','Chinese':'Chinese','Any Other Asian Background':'Other Asian',
 'Black African':'African','Black Caribbean':'Caribbean','Any Other Black Background':'Other Black',
 'Mixed White and Asian':'White and Asian','Mixed White and Black African':'White and Black African',
 'Mixed White and Black Caribbean':'White and Black Caribbean',
 'Any Other Mixed/Multiple Ethnic Background':'Other Mixed or Multiple ethnic groups',
 'Arab':'Arab','Any Other Ethnic Background':'Any other ethnic group'}
FAM = {'White':['English, Welsh, Scottish, Northern Irish or British','Irish',
                'Gypsy or Irish Traveller','Other White'],
 'Asian':['Indian','Pakistani','Bangladeshi','Chinese','Other Asian'],
 'Black':['African','Caribbean','Other Black'],
 'Mixed':['White and Asian','White and Black African','White and Black Caribbean',
          'Other Mixed or Multiple ethnic groups'],
 'Other':['Arab','Any other ethnic group']}
SHORT = {'English, Welsh, Scottish, Northern Irish or British':'White British','Irish':'White Irish',
 'Gypsy or Irish Traveller':'Gypsy/Traveller','Other White':'Other White',
 'Other Mixed or Multiple ethnic groups':'Other Mixed','Any other ethnic group':'Any other'}

REG = {'North East':['Cleveland','Durham','Northumbria'],
 'North West':['Cheshire','Cumbria','Greater Manchester','Lancashire','Merseyside'],
 'Yorkshire and The Humber':['Humberside','North Yorkshire','South Yorkshire','West Yorkshire'],
 'East Midlands':['Derbyshire','Leicestershire','Lincolnshire','Northamptonshire','Nottinghamshire'],
 'West Midlands':['Staffordshire','Warwickshire','West Mercia','West Midlands'],
 'East of England':['Bedfordshire','Cambridgeshire','Essex','Hertfordshire','Norfolk','Suffolk'],
 'London':['London, City of','Metropolitan Police'],
 'South East':['Hampshire','Kent','Surrey','Sussex','Thames Valley'],
 'South West':['Avon & Somerset','Devon & Cornwall','Dorset','Gloucestershire','Wiltshire'],
 'Wales':['Dyfed-Powys','Gwent','North Wales','South Wales']}
SUPER = {'London':['London'],'Midlands':['East Midlands','West Midlands'],
 'South':['South East','South West'],
 'North':['North East','North West','Yorkshire and The Humber'],
 'East&Wls':['East of England','Wales']}          # post01 grouping and order
FLAT = list(REG); COMBINED = ['England and Wales'] + list(SUPER)
GYPSY_FROM = '2021/22'      # code still being adopted before this

df = pd.read_csv(SEARCH).rename(columns={'number_of_stop_and_searches':'n',
                                         'population_by_ethnicity':'pop'})
f2r = {f:r for r,fs in REG.items() for f in fs}
base = df[(df.legislation_type=='All') & (df.geography.isin(f2r))].copy()
base['region'] = base.geography.map(f2r)

nat = df[(df.legislation_type=='All') & (df.geography=='All - excluding BTP') &
         (df.ethnicity_type.str.contains(r'5\+1')) & (df.ethnicity=='White')]
pubcensus = {t:(2021 if g['pop'].iloc[0] > 48.5e6 else 2011) for t,g in nat.groupby('time')}
years = sorted(pubcensus)

b5 = base[base.ethnicity_type.str.contains(r'5\+1')].copy()
b5['k'] = b5.ethnicity.replace({'Other - Including Chinese':'Other'})
b5 = b5[b5.k.isin(['White','Asian','Black','Mixed','Other'])]
bd = base[base.ethnicity_type.str.contains(r'1[689]\+1')].copy()
bd['k'] = bd.ethnicity.map(M); bd = bd[bd.k.notna()]

num = pd.concat([b5,bd]).groupby(['time','region','k'], as_index=False).n.sum()
ew = num.groupby(['time','k'], as_index=False).n.sum(); ew['region'] = 'England and Wales'
num = pd.concat([num, ew])
for sup,parts in SUPER.items():
    if sup in FLAT: continue
    x = num[num.region.isin(parts)].groupby(['time','k'], as_index=False).n.sum(); x['region'] = sup
    num = pd.concat([num, x])
num = num.set_index(['region','time','k']).n.to_dict()

c = pd.read_csv(CENSUS).groupby(['yr','lo','sex','grp','det','region'], as_index=False).n.sum()
add = [c]
e = c.groupby(['yr','lo','sex','grp','det'], as_index=False).n.sum(); e['region'] = 'England and Wales'
add.append(e)
for sup,parts in SUPER.items():
    if sup in FLAT: continue
    x = c[c.region.isin(parts)].groupby(['yr','lo','sex','grp','det'], as_index=False).n.sum()
    x['region'] = sup; add.append(x)
c = pd.concat(add)

KEYS = ['White','Asian','Black','Mixed','Other'] + [d for f in FAM.values() for d in f]
def den(yr, ages, males):
    x = c[c.yr==yr]
    if ages: x = x[x.lo.between(10,30)]
    if males: x = x[x.sex=='Male']
    broad = x.groupby(['region','grp']).n.sum(); detl = x.groupby(['region','det']).n.sum()
    return {**dict(broad.items()), **dict(detl.items())}
DEN = {f'{y}|{"1034" if a else "all"}|{"m" if m else "b"}': den(y,a,m)
       for y in (2011,2021) for a in (False,True) for m in (False,True)}

regions = COMBINED + [r for r in FLAT if r not in COMBINED]
gcut = years.index(GYPSY_FROM)
zeros = 0
out = {}
for r in regions:
    o = {}
    for k in KEYS:
        v = [num.get((r,y,k)) for y in years]
        v = [None if (x is not None and x == 0) else x for x in v]   # a zero is not a measurement
        if k == 'Gypsy or Irish Traveller':
            v = [None if i < gcut else x for i,x in enumerate(v)]
        zeros += sum(1 for y,x in zip(years,v) if num.get((r,y,k)) == 0)
        o[k] = v
    for kk,dd in DEN.items():
        o['den_'+kk] = {k:int(dd.get((r,k),0)) for k in KEYS}
    o['den_pub'] = [{k:int(DEN[f'{pubcensus[y]}|all|b'].get((r,k),0)) for k in KEYS} for y in years]
    out[r] = o

json.dump({'years':years,'regions':regions,'groups':['White','Asian','Black','Mixed','Other'],
           'families':FAM,'short':SHORT,'data':out,
           'geo':[['Combined',COMBINED],['Individual regions',FLAT]]},
          open('ts.json','w'), separators=(',',':'))
print(f'years {len(years)} | areas {len(regions)} | zero cells set to missing: {zeros}')
