# CLAUDE.md — significantfigures.uk

Guidance for Claude Code working in this repository. Read this before editing.

## What this project is

significantfigures.uk is a Quarto static website about critically assessing
statistical claims in the media — teaching readers to question sensationalist or
biased uses of data and verify figures themselves from source. The editorial
spine is: **the benchmark is the argument.** Most misleading claims come not from
false numbers but from the choice of comparison population; the site's job is to
make that choice visible and reproducible.

## Data policy (most important rule)

**Use only openly accessible public data that any reader can download themselves.**

- Every figure must trace to a public source with a followable access path (a URL,
  a named dataset/table code, and the specific selections a reader would make).
- NEVER use, reference, or reintroduce restricted or permission-gated data. In
  particular: no SRS (Secure Research Service) microdata, and no Graduate Outcomes
  (GO) HESA. Earlier versions of this project used these; that era is over. Do not
  reach back for them out of habit from older files or commit history.
- When adding a source, record its access path in the post (or a Data/Methods
  note) so a reader can reproduce the number. If a source isn't publicly
  reproducible, don't use it.

### Known-good public sources

- **England & Wales:** ONS and Nomis (2011 and 2021 censuses). Has true ethnic-group
  data. ONS custom dataset tool for age x sex x ethnic group (e.g. RM032).
- **United States:** US Census Bureau — ACS and decennial, via data.census.gov and
  its public API. Collects race and Hispanic origin, so it has true ethnicity/race
  data (the main non-UK source that does).
- **EU:** Eurostat Data Browser (ec.europa.eu/eurostat/databrowser). Datasets
  migr_pop1ctz (population by age group, sex, citizenship) and migr_pop3ctb (by
  country of birth); five-year age bands, NUTS2/NUTS3 regional. CSV/Excel + API.
- **Nordic countries:** joint portal nordicstatistics.org (harmonised integration/
  migration matrices, foreign-born / descendants / rest-of-population), plus national
  statbanks: scb.se (Sweden), ssb.no (Norway), dst.dk (Denmark), stat.fi (Finland),
  statice.is (Iceland).
- **OECD:** International Migration Database via data-explorer.oecd.org — harmonised
  cross-country stocks/flows by country of birth/nationality, sex, year.
- **UN:** World Population Prospects (population.un.org/wpp) for age x sex population
  by country; UN DESA International Migrant Stock (by age, sex, origin, destination);
  UNSD Demographic Yearbook for census-derived tables.

### Critical methodological caveat: "ethnicity" is not comparable across countries

Outside the UK and US, these sources do NOT collect ethnicity or race. Eurostat and
the Nordic offices break population down by age, sex, citizenship, and country of
birth — using "foreign-born," "descendants" (native-born to foreign-born parents),
and "rest of population" as comparison groups. Some countries (France most strictly)
legally prohibit ethnic statistics. Therefore:

- NEVER present a UK "ethnic group" share next to a continental-European figure as if
  they measure the same thing. They don't. One is ethnicity; the other is birthplace
  or citizenship.
- For cross-country posts, compare like with like: foreign-born vs native-born, or
  shares by country/region of origin — and state explicitly which construct each
  country uses.
- Treat this divergence as content, not friction: that the "minority" is defined by
  ethnicity in one country, birthplace in another, and citizenship in a third is a
  direct illustration of the site's thesis that the benchmark (here, the variable
  itself) is the argument.
- Always name the construct in the post so readers aren't misled into thinking a
  common "ethnicity" measure exists across borders.

## Build and deploy workflow

Hosting is **Cloudflare Pages**, connected to this GitHub repo, deploying on push
to `main`. This is a **pre-built** setup: the site is rendered locally and the
`docs/` output folder is committed; Cloudflare serves those static files as-is.
(GitHub Pages is present in settings but dormant — branch set to `None`. Leave it
off; do not enable it, as a second deployment would conflict.)

Because the render happens locally, the `docs/` folder MUST be rebuilt before
pushing, or the live site won't reflect source edits. The full sequence for any
content or data change:

1. If figures' underlying data or chart code changed: run `python build_figs.py`.
   This script is OUTSIDE the Quarto pipeline — Quarto does not run it. It reads
   the census data, computes representation gaps, and writes interactive Plotly
   charts to `figures/*.html`, which the posts embed. Forgetting this step leaves
   stale charts.
2. Run `quarto render` (writes into `docs/` because `output-dir: docs` is set;
   `execute: freeze: auto` caches unchanged code cells).
3. Commit BOTH the source changes and the regenerated `docs/`.
4. Push to `main`. Cloudflare picks up the push and redeploys.

Never push source-only changes expecting the live site to update — without a fresh
`docs/`, it won't.

For local preview during editing, use `quarto preview`.

## Repository structure

- `_quarto.yml` — project config. Type: website. `output-dir: docs`.
  `site-url: https://significantfigures.uk`. Navbar: Home / the lead post / About.
  Theme: cosmo + custom brand layer + `styles.css`.
- `index.qmd` — home page.
- `post01.qmd` — first post, "Overrepresented compared to whom?" (census data and
  higher-education representation). New posts follow this pattern (`postNN.qmd`).
- `about.qmd` — bio (Maria Boutchkova).
- `data/` — source datasets (e.g. the ONS 2021 census xlsx). Add new public
  datasets here.
- `build_figs.py` — standalone Python/Plotly figure generator (see workflow above).
- `figures/` — generated chart HTML, embedded into posts as iframes.
- `docs/` — rendered output that Cloudflare serves. Generated by `quarto render`;
  committed. Do not hand-edit files in `docs/`.

## Conventions and gotchas

- Custom domain is handled in the Cloudflare dashboard, not via a repo `CNAME`
  file. Do not add a `CNAME` file (that's a GitHub Pages mechanism and irrelevant
  here).
- Keep `site-url` in `_quarto.yml` canonical (`https://significantfigures.uk`) so
  rendered internal links and the sitemap resolve to the custom domain.
- New posts: add the `.qmd`, register it in the navbar/listing in `_quarto.yml` if
  it should appear there, run figures + render, then commit `docs/`.
- Prefer prose and clear methodology over dense tables; the audience includes
  non-programmers who should be able to follow the verification logic.
- When in doubt about whether a data source is allowed, apply the data policy
  above: if a reader can't freely download it and reproduce the number, don't use
  it.
