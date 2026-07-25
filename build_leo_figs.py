"""
build_leo_figs.py  --  LEO sector representation & pay for significantfigures.uk

One figure, two panels side by side:
  left  = Representation  (sector share of women/ABMO minus the overall share
          at the same YAG, in percentage points)
  right = Pay             (ratio of group median earnings to the comparison
          group, as % away from parity)

Buttons switch the demographic (Women / ABMO); both panels update together.
Bars are the YAG series (1, 3, 5, 10) within each sector. Sectors are sorted
best-at-top within each view. Inv / Hybrid / RestFin rows are shaded.

House grammar: Inter, transparent, direct labels, no legend, unified hover.
Data: leo_sect.dta (cr_sic_aggr.do).
"""

import os
import numpy as np
import pandas as pd
import pyreadstat
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from sigfig_style import BODY, BENCH, GRID, FONT

DATA = os.environ.get('SIGFIG_DATA', '.')
OUT  = os.environ.get('SIGFIG_FIG', 'figures')

# YAG series: light -> dark ramp, matching the Stata charts
YAGS   = [1, 3, 5, 10]
YCOLOR = {1: '#bcd4ec', 3: '#7fb0de', 5: '#3f7fc4', 10: '#1b3a6b'}
FIN    = {'Inv', 'Hybrid', 'RestFin'}       # rows to shade

# fixed x-ranges per view (None -> autoscale). Widened slightly from the
# original Stata presets so no bar is clipped (see build note).
XRANGE = {
    ('women', 'rep'): [-35, 25],
    ('abmo',  'rep'): [-20, 25],
    ('women', 'pay'): [-42,  8],
    ('abmo',  'pay'): [-20, 18],
}
# earnings level panel: same under both buttons, in £. Floor at 13k (just
# below the lowest cell, Hosp YAG1 ~13.6k) so no bar clips while still
# giving the high-pay spread room to read.
XRANGE_EARN = [13000, 85000]


# ------------------------------------------------------------------ #
# data prep -- reproduces an_under_over_sic_bar.do
# ------------------------------------------------------------------ #
def load():
    df, meta = pyreadstat.read_dta(os.path.join(DATA, 'leo_sect.dta'))
    labels = meta.variable_value_labels['sect']
    df['sect_name'] = df.sect.map(labels)

    sex = df[df.woman.notna() & df.abmo.isna()].copy()    # Men / Women
    eth = df[df.abmo.notna() & df.woman.isna()].copy()     # White / ABMO

    def rep(dd, grp):
        p = dd.pivot_table(index=['yag_num', 'sect', 'sect_name'],
                           columns=grp, values='count').reset_index()
        p = p.rename(columns={0.0: 'n0', 1.0: 'n1', 0: 'n0', 1: 'n1'})
        p['base'] = p.n0 + p.n1
        p['share'] = 100 * p.n1 / p.base
        tot = p.groupby('yag_num').apply(
            lambda g: 100 * g.n1.sum() / g.base.sum())
        p['overall'] = p.yag_num.map(tot)
        p['val'] = p.share - p.overall
        p['size'] = p.base
        return p[['yag_num', 'sect', 'sect_name', 'val', 'base']]

    def pay(dd, grp):
        p = dd.pivot_table(index=['yag_num', 'sect', 'sect_name'],
                           columns=grp, values='earnings_median').reset_index()
        p = p.rename(columns={0.0: 'e0', 1.0: 'e1', 0: 'e0', 1: 'e1'})
        p['val'] = 100 * (p.e1 / p.e0 - 1)
        return p[['yag_num', 'sect', 'sect_name', 'val']]

    # sector size for the label (share of all hires, pooled over YAG)
    base = df[df.woman.notna() & df.abmo.isna()].groupby(
        ['sect', 'sect_name'])['count'].sum().reset_index(name='sz')
    base['shr'] = 100 * base.sz / base.sz.sum()
    shr = dict(zip(base.sect, base.shr))

    # overall median earnings per sector x YAG (grand-total rows: both NaN).
    # this is the LEVEL panel -- identical under both demographic buttons.
    tot = df[df.woman.isna() & df.abmo.isna()].copy()
    earn = tot[['yag_num', 'sect', 'sect_name', 'earnings_median']].rename(
        columns={'earnings_median': 'val'})

    return {
        ('women', 'rep'): rep(sex, 'woman'),
        ('abmo',  'rep'): rep(eth, 'abmo'),
        ('women', 'pay'): pay(sex, 'woman'),
        ('abmo',  'pay'): pay(eth, 'abmo'),
        ('_', 'earn'): earn,
    }, shr


# ------------------------------------------------------------------ #
# ordering -- best-at-top per view, common to rep & pay of one demog
#            (sector order follows the *representation* panel so the two
#             panels share a y-axis; pay reads against the same order)
# ------------------------------------------------------------------ #
def sector_order(frames, demog):
    rep = frames[(demog, 'rep')]
    mean_rep = rep.groupby(['sect', 'sect_name']).val.mean().reset_index()
    mean_rep = mean_rep.sort_values('val')           # worst first -> bottom
    return mean_rep.sect.tolist(), dict(zip(mean_rep.sect, mean_rep.sect_name))


# ------------------------------------------------------------------ #
# figure
# ------------------------------------------------------------------ #
def build_leo():
    frames, shr = load()

    # y label per sector: "Name  4.2%"
    def ylabels(order, names):
        return [f'{names[s]}  {shr.get(s, float("nan")):.1f}%' for s in order]

    fig = make_subplots(rows=1, cols=3, shared_yaxes=True,
                        horizontal_spacing=0.035,
                        column_widths=[0.36, 0.32, 0.32],
                        subplot_titles=('Representation', 'Pay',
                                        'Median earnings'))

    trace_meta = []      # (demog, panel, yag)

    def add_view(demog, visible):
        order, names = sector_order(frames, demog)
        ypos = {s: i for i, s in enumerate(order)}       # 0 = bottom
        earn = frames[('_', 'earn')]
        panels = (('rep', 1), ('pay', 2), ('earn', 3))
        for panel, col in panels:
            d = earn if panel == 'earn' else frames[(demog, panel)]
            fmt = '£%{x:,.0f}' if panel == 'earn' else '%{x:.1f}'
            for yag in YAGS:
                sd = d[d.yag_num == yag]
                y = [ypos[s] for s in sd.sect]
                fig.add_trace(go.Bar(
                    x=sd.val, y=y, orientation='h',
                    marker=dict(color=YCOLOR[yag], line=dict(width=0)),
                    width=0.18, offset=(YAGS.index(yag) - 1.5) * 0.19,
                    name=f'YAG {yag}',
                    customdata=[names[s] for s in sd.sect],
                    hovertemplate='%{customdata} · YAG ' + str(yag) +
                                  ': ' + fmt + '<extra></extra>',
                    visible=visible, showlegend=False,
                ), row=1, col=col)
                trace_meta.append((demog, panel, yag))
        return order, names

    # both demographics built; women visible first
    order_w, names_w = add_view('women', True)
    order_a, names_a = add_view('abmo', False)

    orders = {'women': (order_w, names_w), 'abmo': (order_a, names_a)}

    # ---- shading bands for the finance carve-outs, all three panels ----
    def shapes_for(demog):
        order, names = orders[demog]
        ypos = {s: i for i, s in enumerate(order)}
        panels = [('x', 'y', XRANGE[(demog, 'rep')]),
                  ('x2', 'y2', XRANGE[(demog, 'pay')]),
                  ('x3', 'y3', XRANGE_EARN)]
        shp = []
        for s in order:
            if names[s] in FIN:
                i = ypos[s]
                for xref, yref, xr in panels:
                    shp.append(dict(type='rect', xref=xref, yref=yref,
                                    x0=xr[0], x1=xr[1], y0=i - 0.5, y1=i + 0.5,
                                    fillcolor='rgba(137,135,129,0.10)',
                                    line=dict(width=0), layer='below'))
        return shp

    def yaxis_for(demog):
        order, names = orders[demog]
        return dict(tickmode='array', tickvals=list(range(len(order))),
                    ticktext=ylabels(order, names))

    # ---- layout ----
    fig.update_layout(
        height=760,
        font=dict(family=FONT, size=12, color=BODY),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=8, r=8, t=96, b=44),
        bargap=0, barmode='overlay', showlegend=False,
        hovermode='closest',
    )
    # x axes: rep & pay diverge from zero; earnings is a £ level panel
    for axname, panel in (('xaxis', 'rep'), ('xaxis2', 'pay')):
        fig.update_layout(**{axname: dict(
            range=XRANGE[('women', panel)], zeroline=True,
            zerolinecolor='#8a8a8a', zerolinewidth=1,
            showgrid=True, gridcolor=GRID,
            ticksuffix=('pp' if panel == 'rep' else '%'),
            title=dict(text=('pp gap vs overall share' if panel == 'rep'
                             else '% from parity'), font=dict(size=11)))})
    fig.update_layout(xaxis3=dict(
        range=XRANGE_EARN, zeroline=False, showgrid=True, gridcolor=GRID,
        tickvals=[20000, 40000, 60000, 80000],
        ticktext=['£20K', '£40K', '£60K', '£80K'],
        title=dict(text='median £ (all graduates)', font=dict(size=11))))
    fig.update_yaxes(**yaxis_for('women'), autorange='reversed',
                     showgrid=False, row=1, col=1)
    fig.update_yaxes(autorange='reversed', showgrid=False, row=1, col=2)
    fig.update_yaxes(autorange='reversed', showgrid=False, row=1, col=3)
    fig.update_layout(shapes=shapes_for('women'))

    # ---- buttons: Women / ABMO -> visibility + y ticks + x ranges + shapes
    def vis(demog):
        return [tm[0] == demog for tm in trace_meta]

    def button(demog, label):
        yx = yaxis_for(demog)
        return dict(label=label, method='update',
                    args=[{'visible': vis(demog)},
                          {'yaxis': dict(yx, autorange='reversed', showgrid=False),
                           'xaxis.range': XRANGE[(demog, 'rep')],
                           'xaxis2.range': XRANGE[(demog, 'pay')],
                           'shapes': shapes_for(demog)}])

    fig.update_layout(
        updatemenus=[dict(type='buttons', direction='right',
                          x=0, xanchor='left', y=1.10, yanchor='top',
                          pad=dict(r=6, t=2, b=2), showactive=True,
                          font=dict(size=12),
                          buttons=[button('women', 'Women'),
                                   button('abmo', 'ABMO')])],
    )

    # YAG colour key, top-right (annotations, static)
    xk = 1.0
    for j, yag in enumerate(YAGS):
        fig.add_annotation(xref='paper', yref='paper',
                           x=xk - (len(YAGS) - 1 - j) * 0.07, y=1.10,
                           xanchor='right', yanchor='top', showarrow=False,
                           text=f'<span style="color:{YCOLOR[yag]}">\u25a0</span> {yag}',
                           font=dict(size=11, color=BODY))
    fig.add_annotation(xref='paper', yref='paper', x=xk - len(YAGS) * 0.07 - 0.005,
                       y=1.10, xanchor='right', yanchor='top', showarrow=False,
                       text='YAG', font=dict(size=11, color=BENCH))
    return fig


def _save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    mode = os.environ.get('SIGFIG_PLOTLYJS', 'inline')
    fig.write_html(path, include_plotlyjs=(True if mode == 'inline' else 'cdn'),
                   full_html=True,
                   config={'displayModeBar': False, 'responsive': True})
    print('wrote', path, f'({mode} plotly.js)')


if __name__ == '__main__':
    _save(build_leo(), 'fig_p3_leo_reppay.html')
