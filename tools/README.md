# Graph exports

`build_graph.py` creates a canonical relationship graph and Amazon Neptune CSV
files from the site's reviewed data. It uses Python 3.10 or newer and the standard
library. It does not contact AWS or modify the site by default.

From the repository root:

```sh
python3 tools/build_graph.py
```

Outputs go to the ignored `build/neptune/` directory. Use `--output PATH` for a
different destination. To explicitly refresh the graph included in the website:

```sh
python3 tools/build_graph.py --write-site
python3 src/build_story.py
```

The `--write-site` option updates `src/data/influence-graph.json` only after the
export checks pass. Review that diff before publishing.

## Inputs and outputs

The six inputs are `src/data/relationships.json`, `people.json`, `companies.json`,
`trump-cases.json`, `crossparty-cases.json` and `fisher-case.json`. The first three
retain the accepted company and beneficiary baseline. The case files add reviewed
political, family, business and financial relationships. The script's explicit
alias map joins identical entities across cases while preserving baseline IDs.
There is no fuzzy identity matching.

| Output | Contents |
| --- | --- |
| `graph.json` | Entity nodes, typed relationships, source register, cases and financial records |
| `alias-map.json` | Explicit identity equivalences used in the export |
| `load/vertices.csv` | Entities, cases, sources and financial-record vertices |
| `load/edges.csv` | Substantive relationships, case membership and provenance edges |
| `validation.json` | Counts, checks, input hashes and load-file hashes |

The November 13, 2026 dataset contains **170 entity nodes and 145 substantive
relationships**. The Neptune files contain **297 vertices and 295 edges** because
they also represent eight cases, 97 sources, 22 financial records and their
provenance connections. A case-membership or source edge is not a financial,
ownership or family connection. These counts describe the reviewed dataset;
they are not coverage estimates for all government spending.

Financial amounts are distinct ledger measures. A reported fee estimate, loan
commitment, company obligation, disclosed income range, alleged payment and
forfeiture order cannot be added into a personal-benefit total. Read the record's
period, recipient, status and qualification. `is_money_flow` identifies a stated
financial route; it does not establish that cash was disbursed. Investment links
identify an owner's asset and do not invent a payment from the asset's issuer.

## Validation and loading

The builder checks ID uniqueness, existing edge endpoints, resolvable citations,
preserved baseline IDs, numeric amounts and CSV/JSON round trips. It retains
range bounds and never copies a case total onto a component relationship.
`validation.json` must report `PASS`; inspect its counts and limitations as well.

Use a new dated or versioned S3 prefix for each reviewed export. Put **only**
`load/vertices.csv` and `load/edges.csv` in the Neptune loader prefix. Keep source
archives, `graph.json`, scripts and validation manifests in separate prefixes.
The loader attempts to parse every file under its input prefix.

The CSVs follow the [Neptune Gremlin load format](https://docs.aws.amazon.com/neptune/latest/userguide/bulk-load-tutorial-format-gremlin.html):
UTF-8, separate vertex/edge files, explicit IDs and scalar properties. Source
lists and full records use JSON strings because Neptune edge properties cannot
use arrays. Vertex scalar properties use single cardinality.

After an authorized import, inspect the loader's final status and detailed
errors. Compare live vertex/edge counts with `validation.json`. Query several
known people, their companies and their cited relationships; counts alone do
not establish correct attribution. Archive the loader result, source-file
hashes, S3 version IDs and the exact export used.

## Corrections and new versions

1. Update the owning source record or case ledger first. Preserve the subject's
   stable identity and add the source, locator, reporting period, financial
   recipient and relevant response or counterevidence. Distinguish a new fact
   from a correction to an earlier claim.
2. Add an explicit alias only after establishing that both IDs describe the
   same entity. Keep subsidiaries, funds, investment instruments, family groups
   and individual relatives separate when their interests are not identical.
3. Run the exporter into a fresh output directory. Review changed nodes, edges,
   amounts, statuses and counts against the prior version. Retain the old export
   and its validation manifest as an immutable audit snapshot.
4. Refresh the site with `--write-site` only after reviewing the export. Keep the
   fiscal window and individual reporting periods explicit.
5. For an existing Neptune dataset, stable IDs permit updates. A loader request
   can use `updateSingleCardinalityProperties=true` to replace existing scalar
   values. Reusing an ID must not silently change an entity's identity or an
   edge's endpoints or relationship type.
6. An import is **not a full synchronization**: missing rows do not delete old
   graph elements, and blank properties do not reliably remove prior values.
   Retractions, removed properties and changed edge endpoints need a separate,
   reviewed migration or a clean versioned dataset. Preserve the correction
   history; never clear a shared graph merely to make its counts match.

No credentials, source archives, deployment account identifiers or generated
bulk files are required in the public repository.
