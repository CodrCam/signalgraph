# SignalGraph

Follow public spending into companies, people and ownership structures.

SignalGraph is a static, source-linked research website covering federal spending, disclosed financial benefits and political influence. The Influence section follows named officials, families, businesses and foreign counterparties, with dated financial measures, reporting, subject responses and source-linked connection trees. Site-wide search spans people, family members, companies and investigations.

## Run locally

Requires Python 3.10 or newer. The build uses the Python standard library; no package installation or backend is required.

```sh
python3 src/build_story.py
python3 -m http.server 8080 --directory src/dist
```

Open `http://localhost:8080`.

## Project files

- `src/data/` — dated financial records, identifiers and source references.
- `src/build_story.py` and related Python modules — page generation.
- `src/pages.js` — browser search and filters.
- `src/influence.py`, `src/influence.js`, `src/influence.css` — investigations, searchable cases, site-wide search and relationship explorers.
- `src/data/influence-graph.json` — canonical relationships, source references and financial meaning for the wider network.
- `src/pages.css`, `src/theme.css`, `src/directory.css` — layout and typography.
- `src/static/assets/` — logo, fonts and font licenses.
- `vercel.json` — deployment configuration.

Generated pages are written to `src/dist/`. The financial window is October 1, 2022 through September 30, 2026; individual disclosures retain their own reporting periods.

## Evidence

Financial entries use a $50,000 threshold for a sourced measure in its stated period. Unpriced ownership and leadership connections remain visible. Corporate obligations, compensation, equity values and personal proceeds are separate measures. Inclusion does not establish misconduct.

Source URLs, dates and limitations accompany the relevant figures. Check the Evidence page and downloadable data before drawing comparisons. Changes to a financial record should retain its stable identifier and update the associated source, period and explanation.

Influence profiles distinguish disclosures, attributed reporting, allegations and adjudicated findings. Historical payments remain visible when later investigations fall within the period, but are excluded from the four-year receipt window. Relationship paths are not summed into personal-income estimates. The site builds without database access; its connection views use the reviewed public snapshot.

## Deployment

Vercel builds the site with `python3 src/build_story.py` and serves `src/dist/`. Fonts are bundled locally; their license files are included with the assets.
