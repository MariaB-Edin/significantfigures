import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

SRC = 'data/census_2021_qual_region_age_sex_ethn.xlsx'
OUT = 'figures'

BENCH = '#898781'   # population share (benchmark)
OBS   = '#2a78d6'   # share holding Level 4+ (observed)
FONT  = 'Inter, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif'

df = pd.read_excel(SRC, sheet_name='Dataset')
df.columns = ['reg_c','reg','q_c','q','age_c','age','sex_c','sex','eth_c','eth','n']
grp = {'London':'London','East Midlands':'Midlands','West Midlands':'Midlands',
       'South East':'South','South West':'South','North East':'North','North West':'North',
       'Yorkshire and The Humber':'North','East of England':'East of England & Wales',
       'Wales':'East of England & Wales'}
df['g'] = df.reg.map(grp)
d = df[(df.q_c != -8) & (df.eth_c != -8)].copy()
d['nonwhite'] = (d.eth_c != 4)
d['l4'] = (d.q_c == 4)

REGIONS = ['London','Midlands','South','North','East of England & Wales']
BANDS = [(4,'20-21'),(5,'22-24'),(6,'25-29'),(7,'30-34'),(8,'35-39'),
         (9,'40-44'),(10,'45-49'),(11,'50+')]

def base_layout(fig, height, title=None):
    fig.update_layout(
        font=dict(family=FONT, size=13, color='#33322e'),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=170, r=40, t=60 if title else 30, b=50),
        height=height, showlegend=False,
        title=dict(text=title, x=0, xanchor='left', font=dict(size=15)) if title else None)
    return fig

# ---------- PART 1: dumbbell, pop share vs L4+ share, by region (22-24) ----------
def p1_stats(mask_name):
    b = d[d.age_c == 5]
    out = {}
    for rg in REGIONS:
        s = b[b.g == rg]; tot = s.n.sum(); l4 = s.loc[s.l4,'n'].sum()
        m = s.nonwhite if mask_name=='nonwhite' else (s.sex==mask_name)
        ps = 100*s.loc[m,'n'].sum()/tot
        ls = 100*s.loc[m & s.l4,'n'].sum()/l4
        out[rg] = (round(ps,1), round(ls,1), round(ls-ps,1), tot/1e6)
    return out

def p1_traces(stats, visible=True):
    ys = [f'{rg}<br><span style="font-size:11px;color:#898781">{stats[rg][3]:.2f}m</span>' for rg in REGIONS]
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
    w, m = p1_stats('Female'), p1_stats('Male')
    ysw, tw = p1_traces(w, True)
    ysm, tm = p1_traces(m, False)
    fig = go.Figure(tw + tm)
    base_layout(fig, 360)
    fig.update_xaxes(range=[42, 62], ticksuffix='%', showgrid=True,
                     gridcolor='rgba(137,135,129,0.18)', zeroline=False)
    fig.add_vline(x=50, line=dict(color=BENCH, width=1, dash='dot'), opacity=0.5)
    fig.update_yaxes(categoryorder='array', categoryarray=list(reversed(ysw)),
                     showgrid=False, ticklabelposition='outside')
    fig.update_layout(annotations=p1_annotations(w, ysw),
        updatemenus=[dict(type='buttons', direction='right', x=0, xanchor='left', y=1.12,
            buttons=[
                dict(label='Women', method='update',
                     args=[{'visible':[True,True,True,False,False,False]},
                           {'annotations':p1_annotations(w, ysw)}]),
                dict(label='Men', method='update',
                     args=[{'visible':[False,False,False,True,True,True]},
                           {'annotations':p1_annotations(m, ysm)}]),
            ])])
    return fig

def build_part1_ethnicity():
    nw = p1_stats('nonwhite')
    ys, tr = p1_traces(nw, True)
    fig = go.Figure(tr)
    base_layout(fig, 360)
    fig.update_xaxes(range=[8, 52], ticksuffix='%', showgrid=True,
                     gridcolor='rgba(137,135,129,0.18)', zeroline=False)
    fig.update_yaxes(categoryorder='array', categoryarray=list(reversed(ys)), showgrid=False)
    fig.update_layout(annotations=p1_annotations(nw, ys))
    return fig

# ---------- PART 2: gap-only lollipop, by age band, per region ----------
def p2_cell(rg, mask_name):
    rows = []
    for ac, lab in BANDS:
        s = d[(d.g==rg) & (d.age_c==ac)]; tot = s.n.sum(); l4 = s.loc[s.l4,'n'].sum()
        m = s.nonwhite if mask_name=='nonwhite' else (s.sex=='Female')
        ps = 100*s.loc[m,'n'].sum()/tot
        ls = 100*s.loc[m & s.l4,'n'].sum()/l4
        rows.append((lab, round(ls,1), round(ls-ps,1)))
    return rows

def build_part2(mask_name, title):
    fig = make_subplots(rows=3, cols=2, subplot_titles=REGIONS + [''],
                        horizontal_spacing=0.13, vertical_spacing=0.10)
    order = list(reversed([b[1] for b in BANDS]))
    for i, rg in enumerate(REGIONS):
        r, c = i//2 + 1, i%2 + 1
        cell = p2_cell(rg, mask_name)
        sx, sy = [], []
        for lab, ls, gap in cell:
            sx += [0, gap, None]; sy += [lab, lab, None]
        fig.add_trace(go.Scatter(x=sx, y=sy, mode='lines',
                      line=dict(color=BENCH, width=2), opacity=0.45, hoverinfo='skip'), row=r, col=c)
        labs = [x[0] for x in cell]; gaps = [x[2] for x in cell]; l4s = [x[1] for x in cell]
        tpos = ['middle right' if g >= 0 else 'middle left' for g in gaps]
        fig.add_trace(go.Scatter(x=gaps, y=labs, mode='markers+text',
                      marker=dict(symbol='circle', size=11, color=OBS),
                      text=[f'{v:.1f}' for v in l4s], textposition=tpos,
                      textfont=dict(size=10, color='#33322e'),
                      customdata=gaps,
                      hovertemplate='%{y}: holds L4+ %{text}%, gap %{customdata:+.1f}pp<extra></extra>'),
                      row=r, col=c)
        fig.add_vline(x=0, line=dict(color=BENCH, width=1.4), opacity=0.8, row=r, col=c)
        fig.update_yaxes(categoryorder='array', categoryarray=order, row=r, col=c,
                         showgrid=False, tickfont=dict(size=11))
        fig.update_xaxes(range=[-5, 8.5], tickvals=[-4,0,4,8], row=r, col=c,
                         showgrid=True, gridcolor='rgba(137,135,129,0.15)', zeroline=False,
                         tickfont=dict(size=10))
    # blank the empty 6th cell
    fig.update_xaxes(visible=False, row=3, col=2); fig.update_yaxes(visible=False, row=3, col=2)
    fig.update_layout(font=dict(family=FONT, size=12, color='#33322e'),
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      height=760, showlegend=False, margin=dict(l=60, r=30, t=70, b=40),
                      title=dict(text=title, x=0, xanchor='left', font=dict(size=15)))
    for a in fig.layout.annotations:
        a.font.size = 13
    return fig

def save(fig, name):
    fig.write_html(f'{OUT}/{name}.html', include_plotlyjs='cdn', full_html=True,
                   config={'displayModeBar':False})
    try:
        fig.write_image(f'{OUT}/{name}.png', scale=2)
    except Exception as e:
        print('PNG failed for', name, ':', e)

if __name__ == '__main__':
    save(build_part1_sex(),        'fig_part1_sex')
    save(build_part1_ethnicity(),  'fig_part1_ethnicity')
    save(build_part2('nonwhite',   'Non-white residents: over/under-representation among Level&nbsp;4+ holders, by age'), 'fig_part2_nonwhite')
    save(build_part2('Female',     'Women: over/under-representation among Level&nbsp;4+ holders, by age'), 'fig_part2_women')
    print('done')
