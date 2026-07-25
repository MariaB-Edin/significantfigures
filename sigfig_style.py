"""Shared house style for significantfigures.uk figures (post01/02 grammar)."""

# palette
BODY  = '#33322e'          # body text
BENCH = '#898781'          # muted / benchmark (Men, White)
OBS   = '#2a78d6'          # observed blue
ACCENT= '#e24b4a'          # warm accent

# four constant series: the "advantaged" line muted, the other carrying accent
SERIES = {
    'Men':   dict(color=BENCH, dash='solid', width=2.0),
    'Women': dict(color=OBS,   dash='solid', width=2.4),
    'White': dict(color=BENCH, dash='dot',   width=2.0),
    'ABMO':  dict(color=ACCENT, dash='dot',  width=2.4),
}

GRID = 'rgba(137,135,129,0.18)'
FONT = 'Inter, system-ui, sans-serif'


def base_layout(fig, height=430):
    fig.update_layout(
        height=height,
        font=dict(family=FONT, size=13, color=BODY),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=8, r=96, t=54, b=36),   # right margin holds the direct labels
        hovermode='x unified',
        showlegend=False,
    )
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False,
                     ticksuffix='%', ticklabelposition='outside')
    fig.update_xaxes(showgrid=False, zeroline=False, dtick=2, tickformat='d')
    return fig
