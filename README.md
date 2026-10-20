# My University View — myuniview.com

Every US postsecondary institution (5,777 of them) on one map, with federal cost,
admissions and athletics data. Static site hosted on GitHub Pages.

## Repository layout

Everything at the repo root is **generated output** — GitHub Pages serves from there,
so the built files have to be committed. Don't hand-edit them; they get overwritten.

```
src/                      SOURCE — edit these
  app_template.html       the whole application: markup, CSS, JS
  homepage.html           the static marketing page served at /
  build_site.py           generator — builds everything below
  db.json                 merged College Scorecard + IPEDS + EADA data
  keys.example.json       copy to keys.json and fill in (keys.json is gitignored)

index.html                GENERATED from src/homepage.html
app/index.html            GENERATED from src/app_template.html
colleges/                 GENERATED — 5,777 school + 59 state + 4 division pages
db.js                     GENERATED from src/db.json
sitemap.xml robots.txt    GENERATED
libs/                     vendored Leaflet, MarkerCluster, Supabase, SheetJS
privacy.html terms.html disclaimer.html sources.html contact.html groups.html
                          hand-maintained; build_site.py does NOT touch these
```

## Rebuilding

```
cd src
cp keys.example.json keys.json      # first time only, then fill it in
python3 build_site.py
```

That writes to `src/site/`. Copy the output up to the repo root:

```
rsync -a src/site/colleges/ colleges/
cp src/site/index.html src/site/app/index.html src/site/sitemap.xml .
```

`rsync` is deliberate — a plain `cp -R` of 5,777 files can fail partway through
and leave the site half-updated, which is easy to miss.

## Two things that will bite you

**The app has three builds, and they are not interchangeable.**
`build_site.py` emits the hosted app at `app/index.html` with asset paths rewritten
to absolute (`/libs/…`, `/db.js`) because it is served from `/app/`. It also emits
`My-University-View.html` with those paths left **relative**, because the Capacitor
iOS bundle loads from `file://` where a leading slash resolves to the device root.
If you add an asset, add it to the rewrite list in `build_site.py` — there is an
assertion that fails the build if any relative path survives into the hosted copy.

**GitHub Pages cannot redirect.** There are no 301s. The app moved from `/` to
`/app/`, so `homepage.html` carries a small script that forwards stale Stripe
returns (`?upgraded=1`) and Supabase OAuth callbacks (`#access_token=…`) to `/app/`.
Don't remove it — without it a customer can pay and land on a marketing page with
nothing unlocked.

## External services

| Service | What it does | Where it's configured |
|---|---|---|
| Supabase | auth, user data, premium flag, licence redemption | project `akktntuteharoczygfku` |
| Stripe | subscriptions ($2.99/mo, $24.99/yr) via Payment Links | webhook → Supabase `stripe-webhook` |
| CARTO | basemap tiles; key is Referer-restricted to myuniview.com | `CARTO_KEY` in `app_template.html` |
| Umami | analytics (`data-exclude-hash` is required — it was logging OAuth tokens) | injected from `keys.json` |

Setting `CARTO_KEY` to `''` reverts the basemap to OpenStreetMap everywhere.
That's the kill switch if CARTO ever fails.

## Data sources

US Department of Education College Scorecard / IPEDS (2022–23) and the federal
Equity in Athletics Disclosure Act survey (2024–25). Cost figures are averages
across all students — see the due-diligence language on every school page.
