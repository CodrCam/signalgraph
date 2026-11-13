#!/usr/bin/env python3
"""Emit safe CSV upserts after comparing an export with the last loaded release."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--previous', type=Path, required=True)
parser.add_argument('--current', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()

def read(path):
    with path.open(newline='', encoding='utf-8') as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        indexed = {row['~id']: row for row in rows}
        if len(rows) != len(indexed):
            raise ValueError(f'Duplicate IDs in {path}')
        return reader.fieldnames, indexed

report = {'status':'PASS','policy':'Upserts only; no deletions, changed labels/endpoints or property clearing','files':{}}
pending = []
for name in ['vertices.csv','edges.csv']:
    headers, old = read(args.previous/name)
    new_headers, new = read(args.current/name)
    if headers != new_headers:
        raise ValueError(f'CSV schema changed: {name}')
    removed = old.keys() - new.keys()
    if removed:
        raise ValueError(f'Removed IDs require an explicit migration: {sorted(removed)}')
    updated = []
    for id_ in old.keys() & new.keys():
        for field in ['~label','~from','~to']:
            if old[id_].get(field) != new[id_].get(field):
                raise ValueError(f'{id_}: {field} cannot change via upsert')
        for field in headers:
            if old[id_][field] and not new[id_][field]:
                raise ValueError(f'{id_}: clearing {field} requires an explicit migration')
        if old[id_] != new[id_]:
            updated.append(id_)
    added = sorted(new.keys()-old.keys())
    ids = added + sorted(updated)
    pending.append((name, headers, [new[id_] for id_ in ids]))
    report['files'][name] = {'previous_count':len(old),'current_count':len(new),'new_ids':added,'updated_ids':sorted(updated),'load_count':len(ids),'removed_ids':[]}

args.output.mkdir(parents=True, exist_ok=True)
for name, headers, rows in pending:
    path = args.output/name
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader(); writer.writerows(rows)
    report['files'][name]['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
(args.output.parent/'delta-validation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({name:{k:v for k,v in data.items() if not k.endswith('_ids')} for name,data in report['files'].items()}, indent=2))
