# SignalGraph

Follow public spending into companies, people and ownership structures.

SignalGraph is a static, source-linked research website covering federal spending, disclosed financial benefits and gaps in the public record. The people directory supports name and company search, company filters, and separate views for disclosed and unpriced entries.

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
- `src/pages.css`, `src/theme.css`, `src/directory.css` — layout and typography.
- `src/static/assets/` — logo, fonts and font licenses.
- `vercel.json` — deployment configuration.

Generated pages are written to `src/dist/`. The financial window is October 1, 2022 through September 30, 2026; individual disclosures retain their own reporting periods.

## Evidence

Financial entries use a $50,000 threshold for a sourced measure in its stated period. Unpriced ownership and leadership connections remain visible. Corporate obligations, compensation, equity values and personal proceeds are separate measures. Inclusion does not establish misconduct.

Source URLs, dates and limitations accompany the relevant figures. Check the Evidence page and downloadable data before drawing comparisons. Changes to a financial record should retain its stable identifier and update the associated source, period and explanation.

## Deployment

Vercel builds the site with `python3 src/build_story.py` and serves `src/dist/`. Fonts are bundled locally; their license files are included with the assets.
