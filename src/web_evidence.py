"""Build short evidence briefs from the reviewed graph, without inferring new links."""
from collections import defaultdict
from html import escape
from pathlib import Path
from urllib.parse import urlparse, quote
import hashlib
import json
import re


def _text(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def _url(value):
    value = _text(value)
    return value if urlparse(value).scheme in ('https', 'http') else ''


def _ids(record):
    return list(dict.fromkeys(record.get('source_ids', []) +
                             ([record['source_id']] if record.get('source_id') else [])))


def _period(record):
    if record.get('period'):
        return _text(record['period'])
    dates = [record.get(k) for k in ('period_start', 'period_end') if record.get(k)]
    if dates:
        return ' – '.join(dates)
    if record.get('announced_date'):
        return 'Announced ' + record['announced_date']
    return _text(record.get('date') or record.get('as_of') or record.get('since'))


def _amount(record):
    amount = record.get('amount_usd', record.get('amount'))
    if isinstance(amount, (int, float)):
        digits = 0 if float(amount).is_integer() else 2
        return ('~' if record.get('approximate') else str(record.get('operator', ''))) + f'${amount:,.{digits}f}'
    low = record.get('min_usd', record.get('amount_min_usd'))
    high = record.get('max_usd', record.get('amount_max_usd'))
    if isinstance(low, (int, float)):
        if isinstance(high, (int, float)):
            return f'${low:,.0f}–${high:,.0f}'
        return ('More than ' if record.get('lower_bound_exclusive') else 'At least ') + f'${low:,.0f}'
    return ''


def safe_source_id(source_id):
    safe = re.sub(r'[^A-Za-z0-9_-]', '-', source_id).strip('-') or 'source'
    if safe != source_id:
        safe += '-' + hashlib.sha256(source_id.encode()).hexdigest()[:8]
    return safe


def _friendly_type(value):
    return {
        'person_or_family': 'Person', 'official': 'Public official', 'person': 'Person',
        'company': 'Company', 'trust': 'Trust', 'government': 'Government',
        'fund_group': 'Investment funds', 'sovereign_investor': 'Sovereign investor',
        'investor_group': 'Investor group', 'organization': 'Organization',
    }.get(value, _text(value).replace('_', ' ').capitalize() or 'Organization')


def _edge_priority(edge):
    """Favor direct economic interests; proximity and family alone rank last."""
    kind = edge.get('relationship_type', edge.get('type', ''))
    if edge.get('money_record') or edge.get('amount_usd') is not None:
        return 0
    if kind in {
        'owns', 'ownership', 'ownership_interest', 'equity_owner', 'equity_investor',
        'minority_ownership', 'reported_ownership', 'indirect_beneficial_owner',
        'disclosed_financial_interest', 'disclosed_investment', 'disclosed_spouse_interest',
        'disclosed_household_interest', 'historical_security_holding', 'beneficiary_of',
        'invests_in', 'capital_commitment', 'loan_commitment', 'loan_obligation',
        'royalties', 'token_proceeds', 'reported_compensation', 'reported_equity_purchase',
    }:
        return 1
    if kind in {'spouse', 'spouse_of', 'parent_of', 'family', 'household_member'}:
        return 5
    return 4


def build_web_evidence(dist, shell, canonical, cases, sources, people, companies):
    """Generate evidence pages and return embeddable briefs plus compact build counts.

    ``shell`` follows the site's (filename, title, body, active, depth, description)
    convention. All facts come from existing reviewed records; graph reachability
    is never promoted into ownership, payment, or a causal claim.
    """
    dist = Path(dist)
    nodes = {n['id']: n for n in canonical.get('nodes', [])}
    overlay_path = Path(__file__).resolve().parent / 'data' / 'ownership-explanations.json'
    ownership = json.loads(overlay_path.read_text()) if overlay_path.exists() else {}
    display_labels = ownership.get('display_labels', {})
    display_types = ownership.get('display_types', {})
    display_name = lambda nid: display_labels.get(nid, nodes[nid]['label'])
    aliases = dict(canonical.get('alias_map', {}))
    for node in nodes.values():
        aliases.update({alias: node['id'] for alias in node.get('alias_ids', [])})
    resolve = lambda value: aliases.get(value, value)
    source_map = dict(sources or {})
    source_map.update(canonical.get('sources', {}))
    edge_ids = {edge['id'] for edge in canonical.get('edges', [])}
    assert set(ownership.get('nodes', {})).issubset(nodes), 'Ownership explanation references an unknown node'
    assert set(ownership.get('edges', {})).issubset(edge_ids), 'Ownership explanation references an unknown edge'
    case_map = {c['id']: c for c in cases}
    people = people.get('people', []) if isinstance(people, dict) else people
    company_rows = companies.get('companies', []) if isinstance(companies, dict) else companies
    profiles = {resolve(p['id']): p for p in people or []}
    company_map = {resolve(c['id']): c for c in company_rows or [] if c.get('id')}
    incident = defaultdict(list)
    node_cases = defaultdict(list)
    source_support = defaultdict(list)
    source_related = defaultdict(set)
    source_case_ids = defaultdict(set)
    source_briefs = {}

    for sid, source in source_map.items():
        source_briefs[sid] = {
            'title': _text(source.get('title') or source.get('name') or 'Supporting record'),
            'publisher': _text(source.get('publisher')) or urlparse(source.get('url', '')).hostname or 'Source record',
            'url': _url(source.get('url')),
            'href': '/evidence/' + safe_source_id(sid) + '.html',
            'date': _text(source.get('date') or source.get('published') or source.get('filed')),
            'locator': _text(source.get('locator') or '; '.join(source.get('locators', []))),
        }

    def source_ids(record):
        return [sid for sid in _ids(record) if sid in source_map]

    def add_support(ids, text, node_ids=(), case_ids=(), qualification=''):
        text = _text(text)
        if not text:
            return
        for sid in ids:
            if sid not in source_map:
                continue
            source_support[sid].append({'text': text, 'qualification': _text(qualification)})
            source_related[sid].update(n for n in node_ids if n in nodes)
            source_case_ids[sid].update(c for c in case_ids if c in case_map)

    for case in cases:
        for node in case.get('nodes', []):
            nid = resolve(node['id'])
            if case['id'] not in node_cases[nid]:
                node_cases[nid].append(case['id'])
        for sid in case.get('source_ids', []):
            if sid in source_map:
                source_case_ids[sid].add(case['id'])
        # Source briefs include reviewed findings and responses, not just graph
        # edges: an article may support a denial or a procurement challenge.
        case_node_ids = [resolve(case.get('root', case.get('root_id')))]
        for item in case.get('findings', []) + case.get('counterevidence', []) + [case.get('response', {})]:
            if item.get('text'):
                add_support(source_ids(item), item['text'], case_node_ids, [case['id']],
                            item.get('period_scope', ''))

    for edge in canonical.get('edges', []):
        a = resolve(edge.get('source', edge.get('from')))
        b = resolve(edge.get('target', edge.get('to')))
        if a not in nodes or b not in nodes:
            continue
        incident[a].append(edge)
        incident[b].append(edge)
        text = f'{display_name(a)} → {display_name(b)}: {_text(edge.get("label") or edge.get("description"))}.'
        period = _period(edge)
        if period:
            text += ' ' + period + '.'
        qualification = edge.get('limitation') or edge.get('qualification', '')
        add_support(source_ids(edge), text, (a, b), edge.get('case_ids', []), qualification)

    for money in canonical.get('money_records', []):
        value = _amount(money)
        recipient = _text(money.get('legal_recipient') or money.get('recipient'))
        if value and recipient:
            text = f'{_text(money.get("label"))}: {value}. Recipient: {recipient}.'
            if _period(money):
                text += ' ' + _period(money) + '.'
            add_support(source_ids(money), text, case_ids=[money.get('case_id')],
                        qualification=money.get('cash_status') or money.get('personal_allocation', ''))

    node_briefs = {}
    for nid, node in nodes.items():
        facts = []
        profile = profiles.get(nid, {})
        role = _text(node.get('role') or profile.get('role'))
        node_sources = source_ids(node)
        if role and node_sources:
            facts.append({'text': role, 'source_ids': node_sources[:3], 'kind': 'role', '_priority': 3})
        for measure in node.get('measurements', []):
            ids = source_ids(measure)
            if not ids or not _amount(measure):
                continue
            text = f'{_text(measure.get("label"))}: {_amount(measure)}.'
            if _period(measure):
                text += ' ' + _period(measure) + '.'
            fact = {'text': text, 'qualification': _text(measure.get('note')),
                    'source_ids': ids, 'kind': 'measurement', '_priority': 0}
            facts.append(fact)
            add_support(ids, f'{node["label"]}: {text}', (nid,), node_cases[nid], measure.get('note', ''))
            if len(facts) >= 3:
                break
        # The selected person's own reviewed case may supply context. An adjacent
        # company's receipt is never silently reassigned to the selected person.
        root_cases = [c for c in cases if resolve(c.get('root', c.get('root_id'))) == nid]
        if root_cases:
            case = root_cases[0]
            findings = [f for f in case.get('findings', []) if f.get('text') and source_ids(f)]
            if findings:
                finding = findings[0]
                facts.append({'text': _text(finding['text']), 'source_ids': source_ids(finding), 'kind': 'finding', '_priority': 2})
        for edge in sorted(incident[nid], key=_edge_priority):
            ids = source_ids(edge)
            if not ids:
                continue
            a = resolve(edge.get('source', edge.get('from')))
            b = resolve(edge.get('target', edge.get('to')))
            if role and _text(edge.get('label')) == role:
                continue
            text = f'{display_name(a)} → {display_name(b)}: {_text(edge.get("label") or edge.get("description"))}.'
            money = edge.get('money_record') or {}
            value = _amount(money)
            if value and value not in text:
                text += ' ' + value + '.'
            if any(f['text'] == text for f in facts):
                continue
            qualification = edge.get('limitation') or (edge.get('qualification') if _edge_priority(edge) < 2 else '')
            facts.append({'text': text, 'source_ids': ids, 'edge_id': edge['id'], 'kind': 'relationship',
                          'period': _period(edge), 'qualification': _text(qualification), '_priority': _edge_priority(edge)})
        facts = sorted(facts, key=lambda fact: fact['_priority'])[:3]
        for fact in facts:
            fact.pop('_priority', None)
        links = []
        profile_url = node.get('profile_url') or (f'people/{profile["slug"]}.html' if profile.get('slug') else '')
        if profile_url and not urlparse(profile_url).scheme and not profile_url.startswith('//'):
            links.append({'label': 'Profile', 'url': '/' + profile_url.lstrip('/')})
        company = company_map.get(nid, {})
        if company.get('slug'):
            links.append({'label': 'Company record', 'url': '/government-spending.html#company-' + quote(company['slug'])})
        for cid in list(dict.fromkeys(node.get('case_ids', []) + node_cases[nid])):
            case = case_map.get(cid)
            if case and case.get('slug'):
                links.append({'label': _text(case.get('title') or case.get('name') or 'Investigation'),
                              'url': '/influence/' + quote(case['slug']) + '.html'})
        node_briefs[nid] = {'name': display_name(nid), 'type': display_types.get(nid, _friendly_type(node.get('type'))),
                            'role': role, 'facts': facts[:3], 'links': links[:5],
                            'source_ids': list(dict.fromkeys(node_sources + [sid for f in facts for sid in f['source_ids']])),
                            'case_ids': node_cases[nid]}
        explanation = ownership.get('nodes', {}).get(nid)
        if explanation:
            for fact in explanation.get('facts', []):
                assert fact.get('source_ids') and all(sid in source_map for sid in fact['source_ids']), 'Unresolved ownership source'
            breakdown = explanation.get('ownership_breakdown', [])
            if breakdown:
                assert sum(row['percent'] for row in breakdown) == 100, 'Ownership breakdown must describe the complete disclosed split'
                assert all(row['owner_id'] in nodes for row in breakdown), 'Unknown owner in ownership breakdown'
            node_briefs[nid].update({
                'name': explanation.get('display_name', display_name(nid)),
                'type': explanation.get('display_type', node_briefs[nid]['type']),
                'facts': explanation.get('facts', [])[:3],
                'source_ids': explanation.get('source_ids', []),
                'ownership_breakdown': breakdown,
                'ownership_note': explanation.get('ownership_note', ''),
                'original_url': _url(explanation.get('original_url')),
                'locator': explanation.get('locator', ''),
                'period': explanation.get('period', ''),
            })

    (dist / 'evidence').mkdir(parents=True, exist_ok=True)
    support_count = 0
    for sid, brief in source_briefs.items():
        source = source_map[sid]
        # Keep the existing source's reuse bound; avoid long article reproductions.
        try:
            budget = min(140, int(source.get('word_limit', source.get('wordlim', 200))))
        except (TypeError, ValueError):
            budget = 140
        chosen, seen, words = [], set(), 0
        for item in source_support[sid]:
            key = item['text'].casefold()
            if key in seen:
                continue
            seen.add(key)
            combined = item['text'] + (' ' + item['qualification'] if item['qualification'] else '')
            cost = len(combined.split())
            if words + cost > budget or len(chosen) >= 8:
                continue
            chosen.append(item)
            words += cost
        support_count += len(chosen)
        body = '<nav class="profile-breadcrumbs wrap" aria-label="Breadcrumbs"><ol><li><a href="../index.html">Home</a></li><li><a href="../connections.html">Connections</a></li><li aria-current="page">Evidence</li></ol></nav>'
        body += '<article class="wrap case-detail evidence-brief"><header class="case-header"><div><span class="eyebrow">Source brief</span><h1 id="content" tabindex="-1">' + escape(brief['title']) + '</h1>'
        body += '<p class="case-period">' + escape(' · '.join(x for x in [brief['publisher'], brief['date']] if x)) + '</p>'
        if brief['locator']:
            body += '<p class="small-note">' + escape(brief['locator']) + '</p>'
        if brief['url']:
            body += '<a class="action-link" href="' + escape(brief['url'], quote=True) + '" target="_blank" rel="noopener noreferrer">Read the original source ↗</a>'
        body += '</div></header><section class="case-findings"><h2>Supports</h2>'
        if chosen:
            body += '<ul>' + ''.join('<li><p>' + escape(item['text']) + '</p>' + ('<p class="small-note">' + escape(item['qualification']) + '</p>' if item['qualification'] else '') + '</li>' for item in chosen) + '</ul>'
        else:
            purpose = _text(source.get('qualification') or source.get('finding'))
            if purpose:
                body += '<p>' + escape(purpose) + '</p>'
            elif brief['locator']:
                body += '<p>The relevant section is ' + escape(brief['locator']) + '.</p>'
            else:
                body += '<p>This record supplies source context for the linked profiles. An ownership stake or payment is established only where the record identifies it.</p>'
        body += '</section>'
        related_cases = [case_map[cid] for cid in sorted(source_case_ids[sid]) if case_map[cid].get('slug')]
        related_nodes = [nodes[nid] for nid in sorted(source_related[sid], key=lambda n: nodes[n]['label'].casefold())]
        if related_cases or related_nodes:
            body += '<section class="case-sources"><h2>Explore</h2><ul>'
            for case in related_cases[:5]:
                label = _text(case.get('name') or case.get('person') or case.get('title'))
                body += '<li><a href="../influence/' + escape(case['slug'], quote=True) + '.html">' + escape(label) + ' · ' + escape(case.get('title', 'Investigation')) + '</a></li>'
            for node in related_nodes[:8]:
                body += '<li><a href="../connections.html?node=' + quote(node['id']) + '">' + escape(display_name(node['id'])) + '</a></li>'
            body += '</ul></section>'
        body += '<p class="small-note">This brief summarizes the cited connection. Ownership, family ties, commitments and payments retain their separate meanings.</p></article>'
        shell('evidence/' + safe_source_id(sid) + '.html', brief['title'], body, 'influence.html', 1,
              description='Evidence and source context for ' + brief['title'])

    for explanation in ownership.get('edges', {}).values():
        assert explanation.get('source_ids') and all(sid in source_map for sid in explanation['source_ids']), 'Unresolved ownership-edge source'
    briefs = {'version': 2, 'nodes': node_briefs, 'sources': source_briefs, 'aliases': aliases,
              'display_labels': display_labels, 'display_types': display_types,
              'edge_explanations': ownership.get('edges', {})}
    path = dist / 'web-briefs.json'
    path.write_text(json.dumps(briefs, ensure_ascii=False, separators=(',', ':')))
    return {'evidence_pages': len(source_briefs), 'node_briefs': len(node_briefs),
            'source_briefs': len(source_briefs), 'supporting_snippets': support_count,
            'briefs_path': str(path), 'briefs': briefs}
