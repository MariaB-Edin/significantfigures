import pandas as pd
import plotly.graph_objects as go

SRC_A = 'data/census_2021_qual_region_age_sex_ethn.xlsx'
SRC_B = 'data/census_2021_yrs_resid_qual_region_age_ethn.xlsx'
OUT = 'figures'

BENCH = '#898781'   # population share (benchmark)
OBS   = '#2a78d6'   # share holding Level 4+ (observed)
FONT  = 'Inter, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif'

BASES = {
    'Regions': ('reg_c', 'reg'),
    'Highest level of qualification': ('q_c', 'q'),
    'Age (B)': ('age_c', 'age'),
    'Sex': ('sex_c', 'sex'),
    'Ethnic group': ('eth_c', 'eth'),
    'Length of residence in the UK': ('lor_c', 'lor'),
}

def rename_by_prefix(df):
    cols = []
    for col in df.columns:
        if col == 'Observation':
            cols.append('n'); continue
        for base, (c_code, c_val) in BASES.items():
            if col.startswith(base):
                cols.append(c_code if col.endswith('Code') else c_val)
                break
        else:
            raise ValueError(f'unmatched column: {col}')
    df = df.copy()
    df.columns = cols
    return df

grp = {'London':'London','East Midlands':'Midlands','West Midlands':'Midlands',
       'South East':'South','South West':'South','North East':'North','North West':'North',
       'Yorkshire and The Humber':'North','East of England':'East of England & Wales',
       'Wales':'East of England & Wales'}

df = rename_by_prefix(pd.read_excel(SRC_A, sheet_name='Dataset'))
df['g'] = df.reg.map(grp)
d = df[(df.q_c != -8) & (df.eth_c != -8)].copy()
d['nonwhite'] = (d.eth_c != 4)
d['l4'] = (d.q_c == 4)

# File B: same population, split by length of residence instead of sex.
# Used for the ethnicity figures so the main claim excludes recent arrivals.
dfb = rename_by_prefix(pd.read_excel(SRC_B, sheet_name='Dataset'))
dfb['g'] = dfb.reg.map(grp)
dr = dfb[(dfb.q_c != -8) & (dfb.eth_c != -8)].copy()
dr['nonwhite'] = (dr.eth_c != 4)
dr['l4'] = (dr.q_c == 4)
dr = dr[~dr.lor_c.isin([4, 5])]

REGIONS = ['London','Midlands','South','North','East of England & Wales']
BANDS = [([2,3],'16-19'),(4,'20-21'),(5,'22-24'),(6,'25-29'),(7,'30-34'),
         (8,'35-39'),(9,'40-44'),(10,'45-49'),(11,'50+')]

def base_layout(fig, height, title=None):
    fig.update_layout(
        font=dict(family=FONT, size=13, color='#33322e'),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=170, r=40, t=60 if title else 30, b=65),
        height=height, showlegend=False,
        title=dict(text=title, x=0, xanchor='left', font=dict(size=15)) if title else None)
    return fig

def caption_annotation(text, width=None):
    ann = dict(x=0, y=-0.18, xref='paper', yref='paper', xanchor='left', yanchor='top',
               text=text, showarrow=False, font=dict(size=11, color='#898781'), align='left')
    if width:
        ann['width'] = width
    return ann

# ---------- PART 1: dumbbell, pop share vs L4+ share, by region (22-24) ----------
def p1_stats(frame, mask_name):
    b = frame[frame.age_c == 5]
    out = {}
    for rg in REGIONS:
        s = b[b.g == rg]; tot = s.n.sum(); l4 = s.loc[s.l4,'n'].sum()
        m = s.nonwhite if mask_name=='nonwhite' else (s.sex==mask_name)
        ps = 100*s.loc[m,'n'].sum()/tot
        ls = 100*s.loc[m & s.l4,'n'].sum()/l4
        out[rg] = (round(ps,1), round(ls,1), round(ls-ps,1), tot/1e3)
    return out

def p1_traces(stats, visible=True):
    ys = [f'{("East&Wls" if rg=="East of England & Wales" else rg)}<br><span style="font-size:11px;color:#898781">{stats[rg][3]:.0f}k</span>' for rg in REGIONS]
    cx, cy = [], []
    for rg, y in zip(REGIONS, ys):
        ps, ls, gap, _ = stats[rg]
        cx += [ps, ls, None]; cy += [y, y, None]
    conn = go.Scatter(x=cx, y=cy, mode='lines', line=dict(color=BENCH, width=2),
                      opacity=0.5, hoverinfo='skip', visible=visible)
    bench = go.Scatter(x=[stats[rg][0] for rg in REGIONS], y=ys, mode='markers',
                       marker=dict(symbol='circle-open', size=13, color=BENCH,
                                   line=dict(width=2, color=BENCH)),
                       hovertemplate='population share %{x:.1f}%<extra></extra>', visible=visible)
    obs = go.Scatter(x=[stats[rg][1] for rg in REGIONS], y=ys, mode='markers',
                     marker=dict(symbol='circle', size=13, color=OBS),
                     hovertemplate='holds Level 4+ %{x:.1f}%<extra></extra>', visible=visible)
    return ys, [conn, bench, obs]

def p1_annotations(stats, ys):
    ann = []
    for rg, y in zip(REGIONS, ys):
        ps, ls, gap, _ = stats[rg]
        lo, hi = (ps, ls) if ps <= ls else (ls, ps)
        ann.append(dict(x=lo, y=y, text=f'{lo:.1f}', showarrow=False, xanchor='right',
                        xshift=-8, font=dict(size=11, color='#6f6d67')))
        ann.append(dict(x=hi, y=y, text=f'{hi:.1f}', showarrow=False, xanchor='left',
                        xshift=8, font=dict(size=11, color='#33322e')))
        sign = '+' if gap >= 0 else '\u2212'
        ann.append(dict(x=(ps+ls)/2, y=y, text=f'{sign}{abs(gap):.1f}', showarrow=False,
                        yshift=15, font=dict(size=11, color='#33322e')))
    return ann

def build_part1_sex():
    w, m = p1_stats(d, 'Female'), p1_stats(d, 'Male')
    ysw, tw = p1_traces(w, True)
    ysm, tm = p1_traces(m, False)
    fig = go.Figure(tw + tm)
    base_layout(fig, 360)
    fig.update_xaxes(range=[42, 62], ticksuffix='%', showgrid=True,
                     gridcolor='rgba(137,135,129,0.18)', zeroline=False)
    fig.add_vline(x=50, line=dict(color=BENCH, width=1, dash='dot'), opacity=0.5)
    fig.update_yaxes(categoryorder='array', categoryarray=list(reversed(ysw)),
                     showgrid=False, ticklabelposition='outside')
    cap = caption_annotation('Number below region name = population count, ages 22–24, in that region')
    fig.update_layout(annotations=p1_annotations(w, ysw) + [cap],
        updatemenus=[dict(type='buttons', direction='right', x=0, xanchor='left', y=1.12,
            buttons=[
                dict(label='Women', method='update',
                     args=[{'visible':[True,True,True,False,False,False]},
                           {'annotations':p1_annotations(w, ysw) + [cap]}]),
                dict(label='Men', method='update',
                     args=[{'visible':[False,False,False,True,True,True]},
                           {'annotations':p1_annotations(m, ysm) + [cap]}]),
            ])])
    return fig

def build_part1_ethnicity():
    nw = p1_stats(dr, 'nonwhite')
    ys, tr = p1_traces(nw, True)
    fig = go.Figure(tr)
    base_layout(fig, 360)
    fig.update_xaxes(range=[8, 52], ticksuffix='%', showgrid=True,
                     gridcolor='rgba(137,135,129,0.18)', zeroline=False)
    fig.update_yaxes(categoryorder='array', categoryarray=list(reversed(ys)), showgrid=False)
    cap = caption_annotation('Number below region name = population count, ages 22–24, '
                             'excluding arrivals within the previous five years')
    fig.update_layout(annotations=p1_annotations(nw, ys) + [cap])
    return fig

# ---------- PART 2: gap-only lollipop, by age band, one region at a time ----------
def p2_cell(frame, rg, mask_name):
    rows = []
    for acs, lab in BANDS:
        ac_list = acs if isinstance(acs, list) else [acs]
        s = frame[(frame.g==rg) & (frame.age_c.isin(ac_list))]
        tot = s.n.sum(); l4 = s.loc[s.l4,'n'].sum()
        m = s.nonwhite if mask_name=='nonwhite' else (s.sex=='Female')
        ps = 100*s.loc[m,'n'].sum()/tot
        ls = 100*s.loc[m & s.l4,'n'].sum()/l4
        rows.append((lab, round(ls,1), round(ls-ps,1), tot))
    return rows

def p2_traces(cell, visible=True):
    labs = [x[0] for x in cell]; l4s = [x[1] for x in cell]; gaps = [x[2] for x in cell]
    sx, sy = [], []
    for lab, ls, gap, tot in cell:
        sx += [0, gap, None]; sy += [lab, lab, None]
    conn = go.Scatter(x=sx, y=sy, mode='lines', line=dict(color=BENCH, width=2),
                      opacity=0.45, hoverinfo='skip', visible=visible)
    tpos = ['middle right' if g >= 0 else 'middle left' for g in gaps]
    pts = go.Scatter(x=gaps, y=labs, mode='markers+text',
                     marker=dict(symbol='circle', size=11, color=OBS),
                     text=[f'{v:.1f}' for v in l4s], textposition=tpos,
                     textfont=dict(size=10, color='#33322e'), customdata=gaps,
                     hovertemplate='%{y}: holds L4+ %{text}%, gap %{customdata:+.1f}pp<extra></extra>',
                     visible=visible)
    return [conn, pts]

def p2_ticktext(cell, order):
    counts = {lab: tot for lab, ls, gap, tot in cell}
    return [f'{lab}<br><span style="font-size:10px;color:#898781">{counts[lab]/1e3:.0f}k</span>' for lab in order]

def build_part2(frame, mask_name, title):
    order = list(reversed([b[1] for b in BANDS]))
    traces, ticktexts = [], []
    for i, rg in enumerate(REGIONS):
        cell = p2_cell(frame, rg, mask_name)
        traces += p2_traces(cell, visible=(i == 0))
        ticktexts.append(p2_ticktext(cell, order))
    fig = go.Figure(traces)
    n = len(REGIONS)
    buttons = []
    for i, rg in enumerate(REGIONS):
        vis = [False] * (2 * n)
        vis[2*i], vis[2*i+1] = True, True
        label = 'East&Wls' if rg == 'East of England & Wales' else rg
        buttons.append(dict(label=label, method='update',
                            args=[{'visible': vis}, {'yaxis.ticktext': ticktexts[i]}]))
    fig.add_vline(x=0, line=dict(color=BENCH, width=1.4), opacity=0.8)
    fig.update_xaxes(range=[-5, 11], tickvals=[-4,0,4,8], showgrid=True,
                     gridcolor='rgba(137,135,129,0.15)', zeroline=False, tickfont=dict(size=11))
    fig.update_yaxes(categoryorder='array', categoryarray=order, showgrid=False, tickfont=dict(size=12),
                     tickmode='array', tickvals=order, ticktext=ticktexts[0])
    cap = caption_annotation("Dot position = gap in percentage points from the population share (line at 0).<br>"
                             "Number by dot = that age band's share of Level 4+ holders.<br>"
                             "Number below age label = population count for that band and region, in '000s.")
    fig.update_layout(font=dict(family=FONT, size=13, color='#33322e'),
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      height=580, showlegend=False, margin=dict(l=70, r=40, t=105, b=130),
                      title=dict(text=title, x=0, xanchor='left', y=1, yanchor='bottom',
                                 yref='paper', pad=dict(b=70), font=dict(size=15)),
                      annotations=[cap],
                      updatemenus=[dict(type='buttons', direction='right', x=0, xanchor='left', y=1.18,
                                        buttons=buttons)])
    return fig

def save(fig, name):
    fig.write_html(f'{OUT}/{name}.html', include_plotlyjs='cdn', full_html=True,
                   config={'displayModeBar':False, 'responsive':True})
    try:
        fig.write_image(f'{OUT}/{name}.png', scale=2)
    except Exception as e:
        print('PNG failed for', name, ':', e)

if __name__ == '__main__':
    save(build_part1_sex(),        'fig_part1_sex')
    save(build_part1_ethnicity(),  'fig_part1_ethnicity')
    save(build_part2(dr, 'nonwhite', 'Non-white residents: over/under-representation among Level&nbsp;4+ holders, by age'), 'fig_part2_nonwhite')
    save(build_part2(d, 'Female',     'Women: over/under-representation among Level&nbsp;4+ holders, by age'), 'fig_part2_women')
    print('done')
