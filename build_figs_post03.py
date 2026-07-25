"""
build_figs.py  --  post03 confounder timelines for significantfigures.uk

One interactive figure. Buttons switch the metric; the four demographic
series (Men, Women, White, ABMO) are always present. Raw shares, no
benchmark transform. Direct right-end labels, no legend, house palette.

Metrics
  employment  employment rate, GB 16-64          2004-2019   (empl file)
  parttime    part-time as % of the employed      2004-2022   (ft/pt file)
  temporary   temporary as % of employees         2004-2022   (temp file)
  l4emp       employment rate, Level 4+ qualified  2012-2022   (qual file)

Data: Ethnicity facts and figures (ONS Annual Population Survey).
"""

import os
import pandas as pd
import plotly.graph_objects as go

from sigfig_style import base_layout, SERIES, BODY

DATA = os.environ.get('SIGFIG_DATA', '.')
OUT  = os.environ.get('SIGFIG_FIG', 'figures')

# ------------------------------------------------------------------ #
# loaders -- normalise the three different schemas to
#   columns: year (int), series in {Men,Women,White,ABMO}, value (float)
# ------------------------------------------------------------------ #
SERIES_ORDER = ['Men', 'Women', 'White', 'ABMO']


def _num(s):
    return pd.to_numeric(s, errors='coerce')


def _yr_plain(s):                       # "2019"
    return _num(s).astype('Int64')


def _yr_janm(s):                        # "Jan2019-Dec2019"
    return _num(s.str.slice(3, 7)).astype('Int64')


def load_employment():
    """empl_region_age_sex_ethn_gb_2004_2019.csv -> employment rate."""
    df = pd.read_csv(os.path.join(DATA, 'empl_region_age_sex_ethn_gb_2004_2019.csv'))
    df = df[(df.Region == 'All') & (df.Age == 'All')].copy()
    df['year'] = _yr_plain(df.Time)
    df['value'] = _num(df.Value)
    rows = []
    rows.append(df[(df.Sex == 'Men')   & (df.Ethnicity_type == 'All')].assign(series='Men'))
    rows.append(df[(df.Sex == 'Women') & (df.Ethnicity_type == 'All')].assign(series='Women'))
    rows.append(df[(df.Sex == 'All') & (df.Ethnicity == 'White') &
                   (df.Ethnicity_type == 'ONS 2011 5+1')].assign(series='White'))
    rows.append(df[(df.Sex == 'All') & (df.Ethnicity == 'Other than White') &
                   (df.Ethnicity_type == 'White and other')].assign(series='ABMO'))
    return pd.concat(rows)[['year', 'series', 'value']].dropna()


def _load_aps(fname, measure_col, measure_val, abmo_key):
    """FT/PT and temp files share a schema; pull one employment_type."""
    df = pd.read_csv(os.path.join(DATA, fname))
    df = df[(df.geography == 'All') & (df[measure_col] == measure_val)].copy()
    df['year'] = _yr_janm(df.time)
    df['value'] = _num(df.value)
    rows = []
    rows.append(df[(df.sex == 'Men')   & (df.ethnicity_type == 'All')].assign(series='Men'))
    rows.append(df[(df.sex == 'Women') & (df.ethnicity_type == 'All')].assign(series='Women'))
    rows.append(df[(df.sex == 'All') & (df.ethnicity == 'White') &
                   (df.ethnicity_type == 'ONS 2011 5+1')].assign(series='White'))
    rows.append(df[(df.sex == 'All') & (df.ethnicity == abmo_key) &
                   (df.ethnicity_type == 'White and other')].assign(series='ABMO'))
    return pd.concat(rows)[['year', 'series', 'value']].dropna()


def load_parttime():
    return _load_aps('employment-by-full-time-and-part-time-2022-data.csv',
                     'employment_type', 'Part-time',
                     'All Other Ethnic Groups Combined (Excluding White Minorities)')


def load_temporary():
    return _load_aps('permanent-and-temporary-employment-2021.csv',
                     'employment_type', 'Temporary',
                     'All Other Ethnic Groups Combined (Excluding White Minorities)')


def load_l4emp():
    """empl_qual_sex_ethn_gb_2012_2022.csv -> employment rate at Level 4+."""
    df = pd.read_csv(os.path.join(DATA, 'empl_qual_sex_ethn_gb_2012_2022.csv'))
    df = df[df.Qualification.str.contains('Level 4', na=False)].copy()
    df['year'] = _yr_plain(df.Time)
    df['value'] = _num(df.Value)
    rows = []
    rows.append(df[(df.Gender == 'Male')   & (df.Ethnicity_type == 'ONS 5+1') &
                   (df.Ethnicity == 'All')].assign(series='Men'))
    rows.append(df[(df.Gender == 'Female') & (df.Ethnicity_type == 'ONS 5+1') &
                   (df.Ethnicity == 'All')].assign(series='Women'))
    rows.append(df[(df.Gender == 'All') & (df.Ethnicity == 'White') &
                   (df.Ethnicity_type == 'ONS 5+1')].assign(series='White'))
    rows.append(df[(df.Gender == 'All') & (df.Ethnicity == 'Other than White') &
                   (df.Ethnicity_type == 'ONS 5+1')].assign(series='ABMO'))
    return pd.concat(rows)[['year', 'series', 'value']].dropna()


# ------------------------------------------------------------------ #
# metric registry
# ------------------------------------------------------------------ #
METRICS = [
    dict(key='employment', label='Employment rate',
         loader=load_employment,
         ytitle='In employment, % of 16–64',
         note='GB, working age 16–64. Employment rate.'),
    dict(key='parttime', label='Part-time',
         loader=load_parttime,
         ytitle='Part-time, % of those in work',
         note='GB. Part-time as a share of people in employment.'),
    dict(key='temporary', label='Temporary',
         loader=load_temporary,
         ytitle='Temporary, % of employees',
         note='GB. Temporary as a share of employees.'),
    dict(key='l4emp', label='Employment at Level 4+',
         loader=load_l4emp,
         ytitle='In employment, % of Level 4+ qualified',
         note='GB, 16–64 holding Level 4+ qualifications. '
              'Framework switches NQF→RQF at 2022; comparable at Level 4+.'),
]


# ------------------------------------------------------------------ #
# figure
# ------------------------------------------------------------------ #
def build_confounders():
    # load every metric, build 4 traces each; only the first metric visible
    frames = {m['key']: m['loader']() for m in METRICS}

    fig = go.Figure()
    trace_meta = []          # (metric_key, series) per trace, to drive buttons

    for mi, m in enumerate(METRICS):
        d = frames[m['key']]
        for s in SERIES_ORDER:
            sd = d[d.series == s].sort_values('year')
            st = SERIES[s]
            fig.add_trace(go.Scatter(
                x=sd.year, y=sd.value, name=s, mode='lines',
                line=dict(color=st['color'], width=st['width'], dash=st['dash']),
                visible=(mi == 0),
                hovertemplate=f'{s}: %{{y:.1f}}%<extra></extra>',
            ))
            trace_meta.append((m['key'], s))

    n = len(trace_meta)

    def right_labels(mkey):
        """direct labels at each series' last point, for the active metric.
        Labels closer than a min gap are spread symmetrically about their
        cluster's centre, so displacement from the true endpoint is minimal
        and the line still visibly points at each label."""
        d = frames[mkey]
        lo, hi = yrange(mkey)
        mingap = 0.065 * (hi - lo)         # min vertical separation, axis units
        pts = []
        for s in SERIES_ORDER:
            sd = d[d.series == s].sort_values('year')
            if sd.empty:
                continue
            pts.append([s, sd.year.iloc[-1], float(sd.value.iloc[-1])])

        # order top->bottom by true value
        order = sorted(range(len(pts)), key=lambda i: -pts[i][2])
        yv = [pts[i][2] for i in order]
        n = len(yv)
        # pass 1: push down to enforce mingap (greedy)
        lab = yv[:]
        for k in range(1, n):
            if lab[k] > lab[k - 1] - mingap:
                lab[k] = lab[k - 1] - mingap
        # pass 2: recentre each maximally-compressed run on its true mean,
        # so the block of labels straddles the real values instead of only
        # hanging below the top one
        k = 0
        while k < n:
            j = k
            while j + 1 < n and abs(lab[j] - lab[j + 1] - mingap) < 1e-9:
                j += 1
            if j > k:                       # run k..j is a tight cluster
                true_c = sum(yv[k:j + 1]) / (j - k + 1)
                lab_c  = sum(lab[k:j + 1]) / (j - k + 1)
                shift  = true_c - lab_c
                for t in range(k, j + 1):
                    lab[t] += shift
            k = j + 1

        laby = {order[r]: lab[r] for r in range(n)}
        ann = []
        for i, (s, x, _yv) in enumerate(pts):
            ann.append(dict(x=x, y=laby[i], text=s,
                            xanchor='left', xshift=8, showarrow=False,
                            font=dict(size=12, color=SERIES[s]['color'])))
        return ann

    def xrange(mkey):
        yr = frames[mkey].year
        return [int(yr.min()) - 0.3, int(yr.max()) + 0.3]

    def yrange(mkey):
        v = frames[mkey].value
        lo, hi = v.min(), v.max()
        pad = 0.08 * (hi - lo + 1e-9)
        return [max(0, lo - pad), hi + pad]

    # buttons: one per metric, toggling trace visibility + axis + labels + note
    buttons = []
    for m in METRICS:
        vis = [tm[0] == m['key'] for tm in trace_meta]
        buttons.append(dict(
            label=m['label'], method='update',
            args=[{'visible': vis},
                  {'annotations': right_labels(m['key']),
                   'xaxis': {'range': xrange(m['key']), 'showgrid': False,
                             'zeroline': False, 'dtick': 2, 'tickformat': 'd'},
                   'yaxis': {'range': yrange(m['key']), 'ticksuffix': '%',
                             'showgrid': True, 'gridcolor': 'rgba(137,135,129,0.18)',
                             'title': {'text': m['ytitle']}},
                   'title': {'text': m['note']}}],
        ))

    base_layout(fig, 470)
    m0 = METRICS[0]
    fig.update_xaxes(range=xrange(m0['key']))
    fig.update_yaxes(range=yrange(m0['key']), title_text=m0['ytitle'])
    fig.update_layout(
        margin=dict(l=8, r=96, t=96, b=36),   # extra top room for title + buttons
        annotations=right_labels(m0['key']),
        title=dict(text=m0['note'], font=dict(size=12, color=BODY),
                   x=0, xanchor='left', y=0.98, yanchor='top'),
        updatemenus=[dict(type='buttons', direction='right',
                          x=0, xanchor='left', y=1.06, yanchor='top',
                          pad=dict(r=6, t=2, b=2), showactive=True,
                          font=dict(size=12),
                          buttons=buttons)],
    )
    return fig


def _save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    # SIGFIG_PLOTLYJS: 'inline' (default, self-contained ~3MB) or 'cdn'
    # (small file, needs a network connection when viewed).
    mode = os.environ.get('SIGFIG_PLOTLYJS', 'inline')
    fig.write_html(path, include_plotlyjs=(True if mode == 'inline' else 'cdn'),
                   full_html=True,
                   config={'displayModeBar': False, 'responsive': True})
    print('wrote', path, f'({mode} plotly.js)')


if __name__ == '__main__':
    _save(build_confounders(), 'fig_p3_confounders.html')
