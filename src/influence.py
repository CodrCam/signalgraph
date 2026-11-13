"""Named influence cases, source-linked relationship views and site-wide search."""
from html import escape as esc
from pathlib import Path
from functools import lru_cache
import json
from web_evidence import build_web_evidence, safe_source_id

ROOT = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def canonical_graph():
    return json.loads((ROOT / 'data' / 'influence-graph.json').read_text())


def connection_link(node, prefix=''):
    graph = canonical_graph()
    node_id = graph['alias_map'].get(node['id'], node['id'])
    assert any(n['id'] == node_id for n in graph['nodes']), f'Unknown linked node: {node_id}'
    return f'<a class="case-node-link" href="{prefix}connections.html?node={esc(node_id,quote=True)}" aria-label="{esc("Explore connections for " + node["label"],quote=True)}">{esc(node["label"])}</a>'


def relationship_period(edge):
    if edge.get('period'):
        return edge['period']
    if edge.get('period_start') or edge.get('period_end'):
        return ' – '.join(str(edge[k]) for k in ['period_start', 'period_end'] if edge.get(k))
    if edge.get('since') and edge.get('as_of'):
        return f'Since {edge["since"]}; observed {edge["as_of"]}'
    if edge.get('announced_date'):
        return f'Announced {edge["announced_date"]}'
    return edge.get('date', edge.get('as_of', edge.get('since', 'Date not specified in this record')))


def load_cases():
    sources, cases = {}, []
    for filename in ['trump-cases.json', 'crossparty-cases.json', 'fisher-case.json', 'beneficiary-stories-cases.json']:
        data = json.loads((ROOT / 'data' / filename).read_text())
        raw_sources = data.get('sources', {})
        sources.update({s['id']: s for s in raw_sources} if isinstance(raw_sources, list) else raw_sources)
        for raw in data.get('cases', [data] if filename == 'fisher-case.json' else []):
            c = dict(raw)
            c['name'] = raw.get('name', raw.get('person', ''))
            c['slug'] = raw.get('slug', {'INF_TRUMP_CRYPTO': 'trump', 'INF_KUSHNER_AFFINITY': 'kushner', 'INF_TRUMPJR_VULCAN': 'trump-jr', 'fisher-contracts': 'fisher', 'BEN_LONDON_CENTENE': 'london', 'INF_MULLIN_FAMILY': 'mullin', 'INF_SCHMIDT_AUTONOMY': 'schmidt'}.get(c['id'], c['id']))
            h = raw.get('headline', {})
            c['display'] = h.get('display', raw.get('headline_amount', ''))
            c['amount_label'] = h.get('label', raw.get('amount_label', ''))
            c['period'] = h.get('period', raw.get('period', ''))
            c['recipient'] = h.get('recipient', raw.get('legal_recipient', {'trump': 'CIC Digital, DT Marks Defi and DT Marks SC', 'kushner': 'Affinity Partners', 'trump-jr': 'Vulcan Elements'}.get(c['slug'], '')))
            c['status'] = raw.get('classification', raw.get('status', raw.get('evidence_status', '')))
            if c['slug'] == 'mills':
                c['summary'] = 'Federal ethics investigators traced nearly $1 million in munitions contracts to companies owned by Rep. Cory Mills after he entered Congress. His wife held leadership roles in the businesses. The Board referred a specific question: whether he improperly benefited from federal contracts while serving in the House.'
            c['historical'] = h.get('window_status') == 'historical_money_in_window_case'
            c['nodes'] = raw.get('nodes', raw.get('graph', {}).get('nodes', []))
            c['edges'] = []
            for i, e in enumerate(raw.get('edges', raw.get('graph', {}).get('edges', []))):
                c['edges'].append({**e, 'id': e.get('id', f'{c["id"]}-{i}'), 'source': e.get('source', e.get('from')), 'target': e.get('target', e.get('to')), 'period': relationship_period(e), 'status': e.get('status', e.get('evidence_status', 'Source-linked relationship'))})
            c['root'] = raw.get('root', raw.get('root_id', {'trump': 'P_TRUMP', 'kushner': 'P_KUSHNER', 'trump-jr': 'P_TRUMPJR', 'fisher': 'IND_TOMMY_FISHER'}.get(c['slug'], c['nodes'][0]['id'])))
            assert c['root'] in {n['id'] for n in c['nodes']}, f'Unknown case root: {c["id"]}'
            c['accountability'] = raw.get('accountability', raw.get('analysis', ''))
            c['response'] = raw.get('response', {'text': 'CBP defended the process as fair, with qualified contractors and reasonable prices. Fisher and Barnard did not respond to the Texas Tribune / ProPublica reporters.', 'source_ids': ['FISHER_TRIBUNE']})
            c['unknowns'] = raw.get('next_evidence', raw.get('open_questions', [raw['missing_fact']] if raw.get('missing_fact') else []))
            c['confidence'] = raw.get('what_is_established', raw.get('confidence_basis', 'Company awards, family leadership and a procurement challenge are documented. Personal distributions and award-specific delivery remain unresolved.'))
            c['limits'] = raw.get('what_is_not_established', '')
            c['role'] = raw.get('role', '; '.join(p['role'] for p in raw.get('people', []) if isinstance(p, dict)))
            c['search'] = ' '.join([c['name'], c['title'], c.get('party') or '', c['summary']] + [n['label'] for n in c['nodes']])
            c['source_ids'] = list(dict.fromkeys(raw.get('source_ids', []) + [s for e in c['edges'] for s in e.get('source_ids', [])] + [s for f in c.get('findings', []) for s in f.get('source_ids', [])] + [s for m in c.get('money', []) for s in m.get('source_ids', [])] + c['response'].get('source_ids', []) + [s for x in c.get('counterevidence', []) for s in x.get('source_ids', [])]))
            cases.append(c)
    order = ['trump', 'pelosi', 'kushner', 'trump-jr', 'fisher', 'mills', 'cuellar', 'menendez', 'london', 'mullin', 'schmidt']
    cases.sort(key=lambda c: (order.index(c['slug']) if c['slug'] in order else len(order), c['name'].casefold()))
    return cases, sources


def card(c, compact=False):
    families = [n for n in c['nodes'] if n['id'] != c['root']][:3]
    tags = f'<span class="case-tag">{esc(c["title"])}</span>'
    if c['historical']:
        tags += '<span class="case-tag historical">Historical payments</span>'
    summary = {
        'trump': 'Trump-linked companies disclosed $1.42 billion in selected 2025 crypto receipts. His trust owns CIC Digital, while other recipient entities have mixed family ownership. A reported UAE investment adds a foreign counterparty.',
        'pelosi': 'Spouse-owned Apple, Amazon and Nvidia holdings produced more than $7 million in reported 2025 income while Nancy Pelosi served in Congress. The disclosure identifies the investments and their income ranges.',
        'kushner': 'Foreign investors pay management fees to the firm Kushner owns while he undertakes diplomacy for his father-in-law. Lawmakers estimated more than $60 million in 2025 firm fees.',
        'trump-jr': '1789 Capital, where Donald Trump Jr. is a partner, invested in Vulcan before the government announced a $620 million loan commitment. Reporting examines White House involvement in that financing decision.',
        'mills': 'Investigators identified nearly $1 million in federal contracts at companies Mills owned while serving in Congress. His wife held leadership roles. The House ethics inquiry examines whether he improperly benefited.'
    }.get(c['slug'], c['summary'])
    return f'''<article class="influence-card{' compact' if compact else ''}" data-case data-search="{esc(c['search'], quote=True)}" data-party="{esc(c.get('party') or 'Family / business', quote=True)}">
      <div class="case-tags">{tags}</div><h3><a href="influence/{c['slug']}.html">{esc(c['name'])}</a></h3>
      <div class="case-amount"><a class="case-amount-link" href="influence/{c['slug']}.html#money" aria-label="{esc(c['display'] + ' — ' + c['amount_label'] + '. View money records for ' + c['name'],quote=True)}">{esc(c['display'])}</a></div><p class="amount-label">{esc(c['amount_label'])}</p>
      <p class="case-recipient"><strong>Recipient</strong> {esc(c['recipient'])}</p><p class="case-period">{esc(c['period'])}</p>
      <p>{esc(summary)}</p><div class="case-links" aria-label="Named connections">{''.join(connection_link(n) for n in families)}</div>
      <a class="case-open" href="influence/{c['slug']}.html">Trace the connections <span aria-hidden="true">↗</span></a></article>'''


def home_feature():
    cases, _ = load_cases()
    selected = [c for c in cases if c['slug'] in ['trump', 'pelosi', 'kushner', 'fisher']]
    return '''<div class="wrap influence-home"><div class="eyebrow-line"><span>Follow the money</span><span>FY2023–FY2026</span></div><div class="home-lead"><div><h1 id="content" tabindex="-1">Power.<br><em>Profit.</em><br>Connections.</h1><p class="deck">The officials, families and businesses behind the money.</p><a class="action-link" href="connections.html">Explore the Web <span aria-hidden="true">↗</span></a></div><div class="home-path"><span>Public power</span><i aria-hidden="true">↓</i><span>Family &amp; business</span><i aria-hidden="true">↓</i><span>Financial benefit</span><p>Follow each link to its source. See what is disclosed, what is reported and what remains unresolved.</p></div></div></div><section class="wrap influence-feature"><div class="influence-section-head"><h2>In Focus</h2><a href="influence.html">All investigations →</a></div><div class="influence-grid">'''+''.join(card(c, True) for c in selected)+'''</div></section><section class="wrap layer-routes"><a href="government-spending.html"><span>01</span><h2>Spending</h2><p>Government commitments, recipient companies and delivery.</p><b aria-hidden="true">→</b></a><a href="individual-benefits.html"><span>02</span><h2>Beneficiaries</h2><p>Executive pay, stock sales, ownership and personal returns.</p><b aria-hidden="true">→</b></a><a href="influence.html"><span>03</span><h2>Influence</h2><p>Public officials, family businesses and foreign money.</p><b aria-hidden="true">→</b></a></section>'''


def beneficiary_stories(cases):
    selected = [c for c in cases if c['slug'] in ['london', 'mullin', 'schmidt']]
    return '<section class="wrap influence-feature"><div class="influence-section-head"><h2>Money Trails</h2><a href="influence.html">All investigations →</a></div><p>Trace the businesses and decisions behind compensation, family investments and government awards.</p><div class="influence-grid">'+''.join(card(c, True) for c in selected)+'</div></section>'


def person_case_links(person, cases, prefix='', detailed=False):
    matches = [c for c in cases if c['root'] == person['id']]
    links = []
    for c in matches:
        href = f'{prefix}influence/{c["slug"]}.html'
        if detailed:
            links.append(f'<div class="influence-prompt"><h2>{esc(c["title"])}</h2><p>{esc(c["summary"])}</p><a href="{esc(href,quote=True)}">Read the full story →</a></div>')
        else:
            links.append(f'<a class="card-link" href="{esc(href,quote=True)}">{esc(c["title"])} <span aria-hidden="true">→</span></a>')
    return ''.join(links)


def fmt_amount(m):
    def dollars(v):
        if abs(v) >= 1e9: return f'${v/1e9:,.2f}B'
        if abs(v) >= 1e6: return f'${v/1e6:,.2f}M'
        return f'${v:,.0f}'
    if m.get('amount_usd') is not None:
        return ('~' if m.get('approximate') else m.get('operator', '')) + dollars(m['amount_usd'])
    minimum = m.get('min_usd', m.get('amount_min_usd'))
    maximum = m.get('max_usd', m.get('amount_max_usd'))
    if minimum is not None:
        if maximum is not None: return f'${minimum:,.0f}–${maximum:,.0f}'
        return ('>' if m.get('lower_bound_exclusive') else '≥') + dollars(minimum)
    return 'Not disclosed'


def build_influence(dist, shell, people, companies):
    cases, sources = load_cases()
    canonical = canonical_graph()
    web = build_web_evidence(dist, shell, canonical, cases, sources, people, companies)
    brief_script = '<script id="web-briefs" type="application/json">' + json.dumps(web['briefs'], ensure_ascii=False).replace('<', '\\u003c') + '</script>'
    def cites(ids):
        return '<span class="case-citations">'+''.join(f'<a href="../evidence/{safe_source_id(sid)}.html">{esc(sources[sid].get("publisher") or sources[sid]["title"].split(" — ")[0])} →</a>' for sid in dict.fromkeys(ids) if sid in sources)+'</span>'

    intro='''<div class="wrap influence-intro"><div class="eyebrow-line"><span>Politics · Family · Money</span><span>FY2023–FY2026</span></div><h1 id="content" tabindex="-1">Influence</h1><p class="deck">Trace the financial interests of officials, families and businesses.</p></div>'''
    controls='''<search class="wrap" aria-label="Influence cases"><form class="influence-filters" data-influence-filter hidden><div><label for="influence-search">Search people, families or companies</label><input type="search" id="influence-search" name="q" placeholder="Pelosi, Trump, Fisher, Affinity…" autocomplete="off" spellcheck="false"></div><div><label for="influence-party">Connections</label><select id="influence-party"><option value="all">All connections</option><option value="Republican">Republican officials</option><option value="Democratic">Democratic officials</option><option value="Family / business">Family &amp; business</option></select></div><button type="reset" class="clear-search">Reset</button></form></search>'''
    intro+='<div class="wrap network-entry"><a href="connections.html">Explore the web →</a></div>'
    body=intro+controls+f'<section class="wrap influence-directory"><h2 class="visually-hidden">Investigations</h2><p id="influence-count" role="status" aria-atomic="true">{len(cases)} investigations</p><div class="influence-grid">'+''.join(card(c) for c in cases)+'</div><p id="influence-empty" class="no-results" hidden>No matching cases. Try a person, company or family name.</p></section><section class="wrap influence-method"><h2>Reading the Record</h2><p><strong>Disclosed</strong> figures come from identified filings. <strong>Reported</strong> findings are attributed to the reporting that supports them. <strong>Alleged</strong> conduct is distinguished from a conviction. Historical payments remain visible when the investigation or judgment falls within the period.</p><a href="influence-evidence.json" download>Case evidence ↓</a></section>'
    shell('influence.html', 'Influence', body, 'influence.html', description='Follow named political figures, their families, business interests and the evidence behind financial benefits.')

    for c in cases:
        body=f'<nav class="profile-breadcrumbs wrap" aria-label="Breadcrumbs"><ol><li><a href="../index.html">Home</a></li><li><a href="../influence.html">Influence</a></li><li aria-current="page">{esc(c["name"])}</li></ol></nav>'
        body+=f'<div class="wrap case-detail"><header class="case-header"><div><span class="eyebrow">{esc(c["title"])} · {esc(c.get("party") or "Family & business")}</span><h1 id="content" tabindex="-1">{esc(c["name"])}</h1><p class="case-role">{esc(c["role"])}</p><p class="deck">{esc(c["summary"])}</p></div><aside class="case-metric"><span class="case-status">{esc(c["status"])}</span><div class="case-amount"><a class="case-amount-link" href="#money" aria-label="{esc(c["display"] + " — view supporting money records",quote=True)}">{esc(c["display"])}</a></div><p class="amount-label">{esc(c["amount_label"])}</p><p><strong>Recipient</strong><br>{esc(c["recipient"])}</p><p class="case-period">{esc(c["period"])}</p>'
        if c['historical']: body+='<p class="historical-note">Historical money. Excluded from FY2023–FY2026 receipt totals.</p>'
        body+='</aside></header><nav class="case-jumps" aria-label="Case sections"><a href="#connections">Connections</a><a href="#findings">Findings</a><a href="#money">Money</a><a href="#response">Response</a><a href="#sources">Sources</a></nav>'
        nodes={n['id']: n for n in c['nodes']}
        graph={'nodes':c['nodes'], 'edges':c['edges'], 'root':c['root'], 'sources':{s:sources[s] for s in c['source_ids'] if s in sources}}
        body+='''<section class="connection-section" id="connections"><div class="influence-section-head"><div><span class="eyebrow">Follow the relationship</span><h2>Connections</h2></div><div class="tree-control" hidden><label for="tree-root">Start with</label><select id="tree-root">'''+''.join(f'<option value="{esc(n["id"],quote=True)}"'+(' selected' if n['id']==c['root'] else '')+'>'+esc(n['label'])+'</option>' for n in c['nodes'])+'''</select></div></div><p class="tree-hint">Explore the people and businesses. Select a name or connection for the evidence.</p><div class="tree-explorer" hidden><div id="connection-tree"></div><aside class="edge-evidence" id="edge-evidence" aria-label="Selected relationship evidence"><h3>Explore</h3><p>Select a name or connection.</p></aside></div><details class="relationship-list" open><summary>All relationships</summary><ul>'''
        for e in c['edges']:
            body+=f'<li><strong>{connection_link(nodes[e["source"]], prefix="../")}</strong> → <strong>{connection_link(nodes[e["target"]], prefix="../")}</strong><br>{esc(e["label"])} <span class="case-period">· {esc(str(e["period"]))}</span>{cites(e.get("source_ids",[]))}</li>'
        canonical_root=canonical['alias_map'].get(c['root'],c['root'])
        body+='</ul></details><p class="network-entry"><a href="../connections.html?node='+esc(canonical_root,quote=True)+'">Explore the web →</a></p></section><script id="case-graph" type="application/json">'+json.dumps(graph,ensure_ascii=False).replace('<','\\u003c')+'</script>'+brief_script
        body+='<section class="case-findings" id="findings"><h2>Findings</h2><ol>'
        for f in c.get('findings',[]): body+='<li>'+('<h3>'+esc(f['label'])+'</h3>' if f.get('label') else '')+'<p>'+esc(f['text'])+'</p>'+cites(f.get('source_ids',[]))+'</li>'
        body+='</ol></section><section class="accountability-box"><span class="eyebrow">The public interest</span><h2>Accountability</h2><p>'+esc(c['accountability'])+'</p></section>'
        body+='<section class="case-money" id="money"><h2>Money</h2><div class="money-grid">'
        for m in c.get('money',[]):
            period=relationship_period(m)
            recipient=m.get('legal_recipient',m.get('recipient',c['recipient']))
            notes=[m.get(k) for k in ['personal_allocation','cash_status','note','aggregation','reason_excluded'] if m.get(k)]
            body+=f'<article class="money-item"><h3>{esc(m["label"])}</h3><strong class="money-value">{esc(fmt_amount(m))}</strong><p><b>Recipient:</b> {esc(recipient)}</p><p class="case-period">{esc(str(period))}</p>'+''.join('<p class="small-note">'+esc(str(n))+'</p>' for n in dict.fromkeys(notes))+cites(m.get('source_ids',[]))+'</article>'
        body+='</div></section><section class="case-response" id="response"><h2>Response</h2><p>'+esc(c['response']['text'])+'</p>'+cites(c['response'].get('source_ids',[]))
        for item in c.get('counterevidence',[]): body+='<p>'+esc(item['text'])+'</p>'+cites(item.get('source_ids',[]))
        body+='</section><section class="case-boundaries"><h2>Evidence</h2><p>'+esc(c['confidence'])+'</p>'
        if c['limits']: body+='<p><strong>Not established:</strong> '+esc(c['limits'])+'</p>'
        body+='</section><section class="case-next"><h2>Unresolved</h2><ul>'+''.join('<li>'+esc(q)+'</li>' for q in c['unknowns'])+'</ul></section><section class="case-sources" id="sources"><h2>Sources</h2><ol>'
        for sid in c['source_ids']:
            if sid not in sources: continue
            s=sources[sid]
            body+=f'<li id="source-{esc(sid,quote=True)}"><a href="{esc(s["url"],quote=True)}" target="_blank" rel="noopener noreferrer">{esc(s["title"])} ↗</a><p>{esc(s.get("publisher", ""))} · {esc(str(s.get("date") or s.get("published") or "Accessed November 13, 2026"))}</p><p class="small-note">{esc(s.get("locator", ""))}</p><a href="../evidence/{safe_source_id(sid)}.html">Source brief →</a></li>'
        body+='</ol></section><p class="case-return"><a href="../influence.html">← All investigations</a><a href="../influence-evidence.json" download>Download case evidence ↓</a></p></div>'
        shell(f'influence/{c["slug"]}.html',c['name'],body,'influence.html',1,description=c['summary'])

    # Search keeps the established directory, companies and political/family cases discoverable together.
    entries=[]
    for c in cases: entries.append({'name':c['name'],'type':'Influence','url':f'influence/{c["slug"]}.html','description':c['title']+' · '+c['display']+' · '+c['amount_label'],'search':c['search']})
    for p in people: entries.append({'name':p['name'],'type':'Beneficiary','url':f'people/{p["slug"]}.html','description':p['company']+' · '+p['role'],'search':' '.join([p['name'],p['company'],p['role'],str(p.get('aliases',''))])})
    for company in companies['companies']: entries.append({'name':company['name'],'type':'Company','url':f'government-spending.html#company-{company["slug"]}','description':company.get('note',''),'search':company['name']})
    body='''<div class="wrap influence-intro"><h1 id="content" tabindex="-1">Search</h1><p class="deck">People, families, companies and their connections.</p></div><search class="wrap" aria-label="All SignalGraph records"><form class="unified-search" action="search.html" method="get"><label for="all-search">Name or company</label><div><input id="all-search" type="search" name="q" autocomplete="off" placeholder="Search every section…"><button class="clear-search" type="submit">Search</button></div></form></search><section class="wrap search-directory"><h2 class="visually-hidden">Search results</h2><p id="search-count" role="status" aria-atomic="true">All records</p><div class="search-results">'''
    for e in entries: body+=f'<article class="search-result" data-search-result data-search="{esc(e["search"],quote=True)}"><span class="eyebrow">{e["type"]}</span><h3><a href="{esc(e["url"],quote=True)}">{esc(e["name"])}</a></h3><p>{esc(e["description"])}</p></article>'
    body+='</div><p id="search-empty" class="no-results" hidden>No matching records. Try a surname, company name or a broader term.</p></section>'
    shell('search.html','Search',body,description='Search SignalGraph people, political families, companies and financial connections.')
    graph_nodes=canonical['nodes']
    graph_sources=canonical['sources']
    graph_edges=[{**e,'type':e.get('relationship_type',e.get('type','relationship')),'period':e.get('period') or e.get('date') or e.get('as_of') or 'Date follows the cited record','status':e.get('evidence_status') or 'Source-linked relationship'} for e in canonical['edges']]
    graph={'nodes':graph_nodes,'edges':graph_edges,'sources':graph_sources,'root':'IND_DONALD_TRUMP','connected_only':True,'max_depth':3}
    body='<div class="wrap influence-intro"><div class="eyebrow-line"><span>Business · Family · Power</span><span>Source-linked relationships</span></div><h1 id="content" tabindex="-1">The Web</h1><p class="deck">Trace the links between officials, families and businesses.</p></div><section class="wrap network-page"><h2 class="visually-hidden">Relationship explorer</h2><div class="tree-control" hidden><label for="tree-root">Start with</label><select id="tree-root">'+''.join(f'<option value="{esc(n["id"],quote=True)}"'+(' selected' if n['id']==graph['root'] else '')+'>'+esc(n['label'])+'</option>' for n in sorted(graph_nodes,key=lambda n:n['label'].casefold()))+'</select></div><p class="tree-hint">Follow a connection. Open the evidence. Find the next question.</p><div class="tree-explorer" hidden><div id="connection-tree"></div><aside class="edge-evidence" id="edge-evidence" aria-label="Selected relationship evidence"><h3>Explore</h3></aside></div><details class="relationship-list" open><summary>All documented relationships</summary><ul>'
    graph_node_map={n['id']:n for n in graph_nodes}
    for e in graph_edges:
        links=' '.join(f'<a href="evidence/{safe_source_id(s)}.html">{esc(graph_sources[s]["title"])} →</a>' for s in e.get('source_ids',[]) if s in graph_sources)
        body+='<li><strong>'+connection_link(graph_node_map[e['source']])+' → '+connection_link(graph_node_map[e['target']])+'</strong><p>'+esc(e['label'])+' · '+esc(str(e['period']))+'</p><span class="case-citations">'+links+'</span></li>'
    body+='</ul></details><div class="case-return"><a href="influence.html">← Investigations</a><a href="influence-graph.json" download>Download the relationship graph ↓</a></div></section><script id="case-graph" type="application/json">'+json.dumps(graph,ensure_ascii=False).replace('<','\\u003c')+'</script>'+brief_script
    shell('connections.html','Web',body,'connections.html',description='Explore source-linked business, family, ownership and financial relationships across SignalGraph investigations.')
    (dist/'influence-evidence.json').write_text(json.dumps({'reviewed_at':'2026-11-13','window':{'start':'2022-10-01','end':'2026-09-30'},'cases':cases,'sources':sources},indent=2,ensure_ascii=False))
    (dist/'influence-graph.json').write_bytes((ROOT/'data'/'influence-graph.json').read_bytes())
    (dist/'sources').mkdir(exist_ok=True)
    (dist/'sources'/'napatree-transactions.json').write_bytes((ROOT/'data'/'napatree-transactions.json').read_bytes())
    return {'influence_cases':len(cases),'influence_sources':len(sources),'search_entries':len(entries),'evidence_pages':web['evidence_pages']}
