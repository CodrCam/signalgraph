#!/usr/bin/env python3
"""Build a provenance-preserving graph from accepted publication inputs only."""
import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARSER = argparse.ArgumentParser(description=__doc__)
PARSER.add_argument('--output', type=Path, default=ROOT / 'build/neptune',
                    help='Output directory (default: build/neptune)')
PARSER.add_argument('--write-site', action='store_true',
                    help='Also update src/data/influence-graph.json after validation')
ARGS = PARSER.parse_args()
OUT = ARGS.output.resolve()
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / 'src/data'
CASE_DIR = BASE
READ = lambda p: json.loads(p.read_text())
WRITE = lambda p, v: p.write_text(json.dumps(v, indent=2, ensure_ascii=False) + '\n')
UNIQ = lambda seq: list(dict.fromkeys(seq))
BASE_GRAPH = READ(BASE / 'relationships.json')
PEOPLE = READ(BASE / 'people.json')
COMPANIES = READ(BASE / 'companies.json')
TRUMP = READ(CASE_DIR / 'trump-cases.json')
CROSS = READ(CASE_DIR / 'crossparty-cases.json')
FISHER = READ(CASE_DIR / 'fisher-case.json')
STORIES = READ(CASE_DIR / 'beneficiary-stories-cases.json')

# Explicit identity equivalence only. Investment instruments and grouped interests
# remain separate from issuers or individuals; no fuzzy identity matching.
ALIASES = {
 'P_TRUMP':'IND_DONALD_TRUMP', 'donald-trump':'IND_DONALD_TRUMP',
 'P_TRUMPJR':'IND_DONALD_TRUMP_JR', 'P_KUSHNER':'IND_JARED_KUSHNER',
 'P_IVANKA':'IND_IVANKA_TRUMP', 'P_ERIC':'IND_ERIC_TRUMP',
 'P_TAHNOON':'IND_TAHNOON_BIN_ZAYED', 'P_MASLIN':'IND_JOHN_MASLIN',
 'TR_TRUST':'TRUST_DONALD_TRUMP_REVOCABLE', 'C_CIC':'ENT_CIC_DIGITAL',
 'C_CELEBRATION':'ENT_CELEBRATION_COINS', 'C_DTTM':'ENT_DTTM_OPERATIONS',
 'C_DJT_HOLD':'ENT_DJT_HOLDINGS', 'C_DJT_MEMBER':'ENT_DJT_HOLDINGS_MANAGING_MEMBER',
 'C_DTTM_MEMBER':'ENT_DTTM_OPERATIONS_MANAGING_MEMBER',
 'C_DEFI_MEMBER':'ENT_DT_MARKS_DEFI_MEMBER', 'C_SC_MEMBER':'ENT_DT_MARKS_SC_MEMBER',
 'C_WLF_HOLD':'ENT_WLF_HOLDCO', 'C_SC_HOLD':'ENT_STABLECOIN_HOLDCO',
 'C_DEFI':'ENT_DT_MARKS_DEFI', 'C_SC':'ENT_DT_MARKS_SC',
 'G_FAMILY_INTERESTS':'GROUP_TRUMP_FAMILY_UNALLOCATED_INTERESTS',
 'C_WLF':'GROUP_WORLD_LIBERTY_RELATED_STRUCTURES',
 'C_ARYAM':'ENT_ARYAM_INVESTMENT_1', 'C_AFFINITY':'ENT_AFFINITY_PARTNERS',
 'F_AFFINITY':'GROUP_AFFINITY_MANAGED_FUNDS', 'SWF_PIF':'ENT_SAUDI_PIF',
 'SWF_QATAR':'GROUP_QATARI_SOVEREIGN_INVESTORS',
 'SWF_UAE':'GROUP_UAE_SOVEREIGN_INVESTORS',
 'G_FOREIGN_LP':'GROUP_AFFINITY_FOREIGN_FEE_PAYERS',
 'C_1789':'ENT_1789_CAPITAL', 'C_VULCAN':'ENT_VULCAN_ELEMENTS',
 'A_OSC':'GOV_OFFICE_STRATEGIC_CAPITAL', 'A_COMMERCE':'GOV_COMMERCE',
 'nancy-pelosi':'IND_NANCY_PELOSI', 'paul-pelosi':'IND_PAUL_PELOSI',
 'apple-stock':'ASSET_APPLE_STOCK', 'amazon-stock':'ASSET_AMAZON_STOCK',
 'nvidia-stock':'ASSET_NVIDIA_STOCK',
 'financial-leasing-services':'ENT_FINANCIAL_LEASING_SERVICES',
 'henry-cuellar':'IND_HENRY_CUELLAR', 'imelda-cuellar':'IND_IMELDA_CUELLAR',
 'imelda-companies':'GROUP_IMELDA_CONTROLLED_COMPANIES',
 'azerbaijan-energy':'GROUP_AZERBAIJANI_STATE_ENERGY_UNNAMED',
 'banco-azteca':'ENT_BANCO_AZTECA',
 'cuellar-intermediaries':'GROUP_CUELLAR_INTERMEDIARIES',
 'robert-menendez':'IND_ROBERT_MENENDEZ',
 'nadine-menendez':'IND_NADINE_MENENDEZ', 'wael-hana':'IND_WAEL_HANA',
 'is-eg-halal':'ENT_IS_EG_HALAL', 'egypt':'GOV_EGYPT',
 'fred-daibes':'IND_FRED_DAIBES', 'jose-uribe':'IND_JOSE_URIBE',
 'cory-mills':'IND_CORY_MILLS', 'rana-al-saadi':'IND_RANA_AL_SAADI',
 'pacem-defense':'ENT_PACEM_DEFENSE', 'als-inc':'ENT_ALS_INC',
 'pacem-solutions':'ENT_PACEM_SOLUTIONS',
 'federal-buyers':'GROUP_BOP_NPS_BUYERS'
}
CANON = lambda id_: ALIASES.get(id_, id_)
sources = dict(PEOPLE['sources'])
for incoming in [TRUMP['sources'], {x['id']:x for x in CROSS['sources']}, FISHER['sources'], STORIES['sources']]:
 for sid, source in incoming.items():
  assert sid not in sources or sources[sid]['url'] == source['url'], f'Source collision {sid}'
  sources[sid] = dict(source, id=sid)
for sid, s in sources.items():
 s['id'] = sid
 s['source_vertex_id'] = 'SOURCE_' + sid
sources['BASELINE_REGISTER'] = {
 'id':'BASELINE_REGISTER', 'title':'SignalGraph accepted entity and relationship register',
 'url':'https://signalgraph-accountability.vercel.app/relationships.json',
 'type':'research_register_provenance', 'source_vertex_id':'SOURCE_BASELINE_REGISTER',
 'qualification':'Identity/cohort provenance only for isolated baseline companies; does not establish an award, ownership, misconduct or personal benefit.'
}

nodes = {n['id']:dict(n, source_ids=[], case_ids=[], origin='accepted_baseline') for n in BASE_GRAPH['nodes']}
for n in nodes.values():
 n['alias_ids'] = []
for p in PEOPLE['people']:
 if p['id'] in nodes:
  n = nodes[p['id']]
  n['source_ids'] = p.get('source_ids', [])
  n['measurements'] = p.get('measurements', [])
  n['role'] = p.get('role', '')
  n['measurement_qualification'] = 'Disclosed compensation, sales, holdings or income retain their own measures and periods; not government-attributed personal receipts.'
for c in COMPANIES['companies']:
 if c['id'] in nodes:
  nodes[c['id']]['source_ids'] += c.get('source_ids', [])

cases = TRUMP['cases'] + CROSS['cases'] + [FISHER] + STORIES['cases']
case_index = {}
money_records = []
edges = []

def source_urls(ids):
 return UNIQ(sources[x]['url'] for x in ids)

def edge_period(e):
 return str(e.get('period') or e.get('date') or e.get('as_of') or e.get('since') or e.get('temporal_scope') or 'Date not established; see cited relationship record')

for e in BASE_GRAPH['edges']:
 edge = dict(e)
 edge.update(label=e.get('description', e.get('relationship_type', 'Relationship')), period=edge_period(e),
             qualification=e.get('description', '') + ' No government-attributed personal cash amount is established by this relationship.',
             is_money_flow=False, is_financial_relationship=False, amount_usd=None,
             amount_recipient_id=None, case_ids=[], origin='accepted_baseline')
 edge['source_urls'] = source_urls(edge['source_ids'])
 edges.append(edge)

for case in cases:
 cid = case['id']
 cg = case.get('graph', case)
 case_money = {m.get('id', f'{cid}_M{i+1}'): dict(m, id=m.get('id', f'{cid}_M{i+1}'), case_id=cid) for i,m in enumerate(case.get('money', []))}
 case_sources = UNIQ(case.get('source_ids', []) + [sid for e in cg['edges'] for sid in e.get('source_ids', [])] + [sid for m in case_money.values() for sid in m.get('source_ids', [])])
 case_index[cid] = {
  'id':cid, 'title':case['title'], 'person':case.get('person', case.get('name')),
  'summary':case.get('summary'), 'source_ids':case_sources,
  'source_urls':source_urls(case_sources),
  'node_ids':[CANON(n['id']) for n in cg['nodes']],
  'evidence_status':case.get('status', case.get('classification', case.get('evidence_status'))),
  'qualification':case.get('what_is_not_established', case.get('missing_fact', case.get('publication_limits'))),
  'money_ids':list(case_money)
 }
 for n in cg['nodes']:
  nid = CANON(n['id'])
  if nid not in nodes:
   nodes[nid] = dict(n, id=nid, source_ids=[], case_ids=[], alias_ids=[], origin='independently_reviewed_case')
  dest = nodes[nid]
  dest['case_ids'] = UNIQ(dest['case_ids'] + [cid])
  dest['source_ids'] = UNIQ(dest['source_ids'] + n.get('source_ids', []))
  if nid != n['id']: dest['alias_ids'] = UNIQ(dest['alias_ids'] + [n['id']])
 for i, original in enumerate(cg['edges']):
  e = dict(original)
  e['id'] = original.get('id') or 'INF_' + cid.upper().replace('-','_') + '_' + str(i+1).zfill(2)
  e['source'] = CANON(original.get('source', original.get('from')))
  e['target'] = CANON(original.get('target', original.get('to')))
  e['relationship_type'] = original.get('relationship_type', original.get('type', 'relationship'))
  e['period'] = edge_period(e)
  e['case_ids'] = [cid]
  e['source_urls'] = source_urls(e['source_ids'])
  e['origin'] = 'independently_reviewed_case'
  m = case_money.get(e.get('money_id'), {})
  e['money_record'] = m or None
  e['is_financial_relationship'] = bool(m or e.get('amount_usd') is not None or e['relationship_type'] in ['bribery_benefit','alleged_payment_route'])
  # "Money flow" describes an asserted financial link, not an assertion of cash
  # paid. Read cash_status and amount semantics before interpreting the edge.
  e['is_money_flow'] = e['is_financial_relationship'] and e['relationship_type'] != 'disclosed_investment'
  e['cash_status'] = m.get('cash_status') or m.get('type') or ('net_obligations_not_outlays' if e['relationship_type']=='government_obligation' else 'not_established')
  e['amount_usd'] = e.get('amount_usd')
  # A component edge is never assigned its containing case's total.
  e['amount_recipient_id'] = (e['source'] if e['relationship_type']=='disclosed_investment' else e['target']) if e['is_financial_relationship'] else None
  e['amount_semantics'] = m.get('type') or ('company_net_contract_obligations' if e['relationship_type']=='government_obligation' else 'No amount assigned')
  e['evidence_status'] = original.get('evidence_status') or original.get('status') or ('reported' if 'reported' in e['relationship_type'] or 'FISHER_AXIOS' in e['source_ids'] else 'attributed_estimate' if 'estimated' in e['relationship_type'] else 'documented_relationship')
  e['qualification'] = ' '.join(str(v) for v in [m.get('personal_allocation'), m.get('cash_counterparty'), m.get('aggregation'), m.get('cash_status'), m.get('reason_excluded')] if v)
  if not e['qualification']:
   e['qualification'] = 'Company net obligations; not outlays, profit or personal proceeds.' if e['relationship_type']=='government_obligation' else 'Relationship only; no personal payment or causal influence inferred from this edge.'
  if case in STORIES['cases']:
   e['qualification'] = ' '.join(UNIQ([v for v in [original.get('qualification'), e['qualification']] if v]))
   if original.get('cash_status'): e['cash_status'] = original['cash_status']
   if original.get('is_money_flow') is False: e['is_money_flow'] = False
   if original.get('amount_recipient_id'): e['amount_recipient_id'] = CANON(original['amount_recipient_id'])
  years = [int(y) for y in re.findall(r'(?<!\d)(?:19|20)\d{2}(?!\d)', e['period'])]
  historical = bool(original.get('outside_window') or m.get('include_in_window_total') is False or ('historical context' in e['period']) or (years and max(years)<2022))
  inside = bool(years and min(years)>=2023 and max(years)<=2025)
  # An undated relationship or a boundary-year date is not asserted to be in
  # the frozen fiscal window. Human-readable periods remain authoritative.
  e['outside_window'] = True if historical else False if inside else None
  e['window_status'] = 'historical_context' if historical else 'within_window' if inside else 'mixed_boundary_or_not_dated'
  if original.get('window_status') is not None:
   assert original['window_status'] in ('historical_context','within_window','mixed_boundary_or_not_dated'), f"Invalid window status {e['id']}"
   e['window_status'] = original['window_status']
   e['outside_window'] = {'historical_context':True,'within_window':False,'mixed_boundary_or_not_dated':None}[e['window_status']]
  e['government_attributed_personal_receipts_usd'] = None
  edges.append(e)
 for m in case_money.values():
  m['source_urls'] = source_urls(m.get('source_ids', []))
  m['graph_vertex_id'] = 'MONEY_' + m['id']
  m['aggregate_personal_income_eligible'] = False
  money_records.append(m)

# Merge personal disclosures after new case nodes have been created.
for p in PEOPLE['people']:
 if p['id'] in nodes and nodes[p['id']]['origin'] != 'accepted_baseline':
  n = nodes[p['id']]
  n['source_ids'] = UNIQ(n['source_ids'] + p.get('source_ids', []))
  n['measurements'] = p.get('measurements', [])
  n['role'] = p.get('role', '')
  n['measurement_qualification'] = 'Disclosed personal measures are not automatically government-attributed receipts.'

# Populate node evidence from the exact incident claims; an edge carries the
# claim-level citation and this union is only navigation/provenance metadata.
for e in edges:
 for nid in [e['source'],e['target']]:
  nodes[nid]['source_ids'] = UNIQ(nodes[nid]['source_ids'] + e['source_ids'])
for n in nodes.values():
 if n['origin'] == 'accepted_baseline' and any(cid in {c['id'] for c in STORIES['cases']} for cid in n['case_ids']):
  n['evidence_status'] = 'source_linked_relationships'
 if not n['source_ids']:
  n['source_ids'] = ['BASELINE_REGISTER']
  n['evidence_status'] = 'identity_in_research_cohort_only'
 n['source_urls'] = source_urls(n['source_ids'])

graph = {
 'schema_version':'signalgraph-canonical-1.0', 'review_date':'2026-11-13',
 'window':{'start':'2022-10-01','end':'2026-09-30','label':'FY2023–FY2026'},
 'scope':f'Accepted baseline plus {len(cases)} independently reviewed cases. Historical context and subsequent legal/source events are labeled. Neither sums nor infers personal government receipts.',
 'semantics':{'is_money_flow':'Asserted financial route, including obligations, commitments, estimates or alleged payments; cash_status distinguishes actual receipt. False for disclosed-investment links because the issuer is not identified as cash counterparty.',
  'amount_usd':'Only an amount explicitly assigned to the edge. Case totals are never copied to component edges.',
  'amount_recipient_id':'Recipient of the described financial measure, not necessarily the arrow target; investment links point from owner to asset.',
  'source_ids':'Resolvable in sources; identical IDs also exist as SOURCE_<id> vertices in Neptune.',
  'measurements':'Baseline personal disclosures retained on their existing nodes; not government-attributed income.'},
 'nodes':list(nodes.values()), 'edges':edges, 'sources':sources,
 'cases':list(case_index.values()), 'money_records':money_records, 'alias_map':ALIASES
}

# Neptune uses separate vertex and edge CSV files. JSON is serialized as scalar
# String properties, never Neptune array properties (unsupported on edges).
vertices = [dict(n, name=n['label'], vertex_kind='entity') for n in nodes.values()]
support_edges = []
for sid,s in sources.items():
 vertices.append(dict(s, id=s['source_vertex_id'], label=s['title'], name=s['title'], type='source', vertex_kind='source', source_ids=[sid], source_urls=[s['url']]))
for cid,c in case_index.items():
 cv = 'CASE_' + cid
 vertices.append(dict(c, id=cv, label=c['title'], name=c['title'], type='case', vertex_kind='case'))
 for nid in c['node_ids']:
  support_edges.append({'id':'CASE_MEMBER_'+cid+'_'+nid, 'source':cv,'target':nid,'relationship_type':'INCLUDES_ENTITY','label':'Case includes entity','case_ids':[cid]})
 for sid in c['source_ids']:
  support_edges.append({'id':'CASE_SOURCE_'+cid+'_'+sid,'source':cv,'target':'SOURCE_'+sid,'relationship_type':'SOURCED_FROM','label':'Case source','source_ids':[sid]})
for m in money_records:
 vertices.append(dict(m,id=m['graph_vertex_id'],record_id=m['id'],label=m['label'],name=m['label'],vertex_kind='financial_record',financial_type=m.get('type'),type='financial_record',case_ids=[m['case_id']]))
 support_edges.append({'id':'CASE_MONEY_'+m['id'],'source':'CASE_'+m['case_id'],'target':m['graph_vertex_id'],'relationship_type':'HAS_FINANCIAL_RECORD','label':'Financial record','case_ids':[m['case_id']]})
 for sid in m.get('source_ids',[]):
  support_edges.append({'id':'MONEY_SOURCE_'+m['id']+'_'+sid,'source':m['graph_vertex_id'],'target':'SOURCE_'+sid,'relationship_type':'SOURCED_FROM','label':'Financial source','source_ids':[sid]})
csv_edges = edges + support_edges

errors = []
def check(condition, message):
 if not condition: errors.append(message)
check(len(nodes)==len(set(nodes)), 'Duplicate domain node IDs')
check(len(edges)==len({e['id'] for e in edges}), 'Duplicate domain edge IDs')
v_ids = {v['id'] for v in vertices}
check(len(vertices)==len(v_ids), 'Duplicate Neptune vertex IDs')
check(len(csv_edges)==len({e['id'] for e in csv_edges}), 'Duplicate Neptune edge IDs')
check(set(n['id'] for n in BASE_GRAPH['nodes']).issubset(nodes), 'Lost baseline nodes')
check(set(e['id'] for e in BASE_GRAPH['edges']).issubset(e['id'] for e in edges), 'Lost baseline edges')
for e in csv_edges:
 check(e['source'] in v_ids and e['target'] in v_ids, f"Missing endpoint {e['id']}")
 for sid in e.get('source_ids',[]): check(sid in sources, f"Unknown source {sid}")
 if e in edges: check(bool(e.get('source_ids')), f"Uncited domain edge {e['id']}")
 if e.get('amount_usd') is not None:
  check(isinstance(e['amount_usd'],(float,int)) and math.isfinite(e['amount_usd']), f"Invalid amount {e['id']}")
  check(bool(e.get('amount_recipient_id')),f"Missing recipient semantics {e['id']}")
for sid,s in sources.items(): check(s.get('url','').startswith(('https://','http://')), f'Invalid source URL {sid}')
for m in money_records:
 check(bool(m.get('source_ids')),f"Uncited money record {m['id']}")
 check(m['aggregate_personal_income_eligible'] is False,f"Unexpected personal aggregation {m['id']}")
assert not errors, '\n'.join(errors)

def js(v): return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def csv_write(path, headers, records, edge=False):
 with path.open('w',encoding='utf-8',newline='') as f:
  writer=csv.writer(f,lineterminator='\r\n'); writer.writerow(headers)
  for r in records:
   row=[]
   for h in headers:
    field=h.split(':')[0]
    if field=='~id': v=r['id']
    elif field=='~label': v=r['relationship_type'] if edge else r['type']
    elif field=='~from': v=r['source']
    elif field=='~to': v=r['target']
    elif field=='properties_json': v=js(r)
    elif field.endswith('_json'): v=js(r.get(field[:-5],[]))
    elif field=='claim_qualification': v=r.get('qualification','')
    else: v=r.get(field)
    if isinstance(v,bool): v=str(v).lower()
    elif isinstance(v,(list,dict)): v=js(v)
    row.append(v)
   writer.writerow(row)
VH=['~id','~label','name:String(single)','vertex_kind:String(single)','source_ids_json:String(single)','source_urls_json:String(single)','case_ids_json:String(single)','profile_url:String(single)','evidence_status:String(single)','amount_usd:Double(single)','min_usd:Double(single)','max_usd:Double(single)','lower_bound_exclusive:Bool(single)','period:String(single)','financial_type:String(single)','properties_json:String(single)']
EH=['~id','~from','~to','~label','label:String','source_ids_json:String','source_urls_json:String','case_ids_json:String','period:String','evidence_status:String','claim_qualification:String','is_money_flow:Bool','is_financial_relationship:Bool','amount_usd:Double','amount_recipient_id:String','amount_semantics:String','cash_status:String','outside_window:Bool','properties_json:String']
LOAD=OUT/'load'; LOAD.mkdir(exist_ok=True)
csv_write(LOAD/'vertices.csv',VH,vertices)
csv_write(LOAD/'edges.csv',EH,csv_edges,True)
for path, headers, expected in [(LOAD/'vertices.csv',VH,len(vertices)),(LOAD/'edges.csv',EH,len(csv_edges))]:
 with path.open(encoding='utf-8',newline='') as f:
  reader=csv.reader(f); check(next(reader)==headers,f'Header mismatch {path}')
  rows=list(reader); check(len(rows)==expected,f'Row count mismatch {path}')
  check(all(len(r)==len(headers) for r in rows),f'Malformed CSV {path}')
  for r in rows:
   try: json.loads(r[-1])
   except Exception: errors.append(f'Invalid properties JSON in {path}')
assert not errors, '\n'.join(errors)
WRITE(OUT/'graph.json',graph)
WRITE(OUT/'alias-map.json',{'policy':'Explicit same-identity mappings; preserves baseline IDs; no fuzzy matching or ownership inference. Grouped and instrumental entities stay separate.', 'aliases':ALIASES})
inputs=[BASE/'relationships.json',BASE/'people.json',BASE/'companies.json',CASE_DIR/'trump-cases.json',CASE_DIR/'crossparty-cases.json',CASE_DIR/'fisher-case.json',CASE_DIR/'beneficiary-stories-cases.json']
validation={
 'status':'PASS', 'review_date':'2026-11-13', 'errors':errors,
 'counts':{'baseline_nodes':len(BASE_GRAPH['nodes']),'baseline_edges':len(BASE_GRAPH['edges']), 'domain_nodes':len(nodes),'domain_edges':len(edges),'sources':len(sources),'cases':len(cases),'money_records':len(money_records),'neptune_vertices':len(vertices),'neptune_edges':len(csv_edges),'financial_relationship_edges':sum(bool(e.get('is_financial_relationship')) for e in edges)},
 'checks':['Every baseline node and edge ID preserved','Every domain edge has resolvable citations','Every edge endpoint exists','Explicit alias map applied; grouped interests not assigned to individuals','CSV round trip, required headers, unique IDs and JSON properties validated','No case total copied to component edges','No aggregate personal-government-income field or sum','Repair graph excluded; no unverifiable recipient IDs imported'],
 'limitations':['Source access quality varies and is recorded in source metadata; inclusion is not a fresh adjudication of every baseline filing','Historical and alleged relationships are included with status and period, not treated as established personal cash','Isolated original company nodes retain research-register provenance only','Neptune live import has not been executed by this builder'],
 'inputs':[{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in inputs],
 'load_files':[{'path':str(p.relative_to(OUT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in [LOAD/'vertices.csv',LOAD/'edges.csv']],
 'format_reference':'https://docs.aws.amazon.com/neptune/latest/userguide/bulk-load-tutorial-format-gremlin.html'
}
WRITE(OUT/'validation.json',validation)
if ARGS.write_site:
 WRITE(BASE/'influence-graph.json',graph)
print(json.dumps(validation['counts'],indent=2))
