"""Build a static, source-linked investigation and one page per named entry."""
from pathlib import Path
from html import escape as esc
import json
import re
import shutil
import hashlib
from reconciliation import channels, transactions, followups, audit
from presentation import compact_headings
from directory_ui import render_directory

THRESHOLD = 50_000

ROOT = Path(__file__).resolve().parent
FILES = [('government-spending.html','Spending'),('individual-benefits.html','Beneficiaries'),('blind-spots.html','Blind Spots'),('methods.html','Evidence')]

def money(value):
    if value is None: return 'Unquantified'
    if abs(value) >= 1e12: return f'${value/1e12:,.2f}T'
    if abs(value) >= 1e9: return f'${value/1e9:,.2f}B'
    if abs(value) >= 1e6: return f'${value/1e6:,.2f}M'
    return f'${value:,.0f}'

def external(url, title, css='source-link'):
    return f'<a class="{css}" href="{esc(url,quote=True)}" target="_blank" rel="noopener noreferrer">{esc(title)} <span aria-hidden="true">↗</span></a>'

def build_multipage(dist, evidence):
    original=(dist/'index.html').read_text()
    review=json.loads((ROOT/'data'/'beneficiaries.json').read_text())
    directory=json.loads((ROOT/'data'/'people.json').read_text())
    companies=json.loads((ROOT/'data'/'companies.json').read_text())
    reconciliation=json.loads((ROOT/'data'/'reconciliation.json').read_text())
    people=directory['people']; source_map=directory['sources']
    assets=dist/'assets'; assets.mkdir(exist_ok=True)
    base='\n'.join(re.findall(r'<style>(.*?)</style>', original,re.S)).replace("url('assets/","url('")
    (assets/'base.css').write_text(base)
    for asset in ['pages.css','pages.js','theme.css','directory.css']:
        shutil.copy2(ROOT/asset, assets/asset)
    asset_revision=hashlib.sha256(b''.join((assets/name).read_bytes() for name in ['base.css','pages.css','pages.js','theme.css','directory.css'])).hexdigest()[:12]
    shutil.copy2(ROOT/'data'/'people.json',dist/'people-evidence.json')
    shutil.copy2(ROOT/'data'/'companies.json',dist/'company-index.json')
    (dist/'research-agent-prompt.txt').unlink(missing_ok=True)
    for filename in ['relationships.json','transactions-evidence.json']:
        shutil.copy2(ROOT/'data'/filename,dist/filename)
    shutil.copy2(ROOT/'data'/'reconciliation.json',dist/'reconciliation-audit.json')
    total=sum(x['aggregated_amount'] for x in review['spending']['totals']['response']['results'])
    yearly=review['spending']['totals']['response']['results']
    highest=max(x['aggregated_amount'] for x in yearly)
    home_bars=''.join(f'<span class="{"tentative" if x["time_period"]["fiscal_year"]=="2026" else ""}" style="height:{100*x["aggregated_amount"]/highest:.4f}%"><b>{x["time_period"]["fiscal_year"]}</b></span>' for x in yearly)
    qualified=[p for p in people if p['qualifies']]
    unknown=[p for p in people if not p['qualifies']]
    profile_dir=dist/'people';profile_dir.mkdir(exist_ok=True)

    def section(sid):
        match=re.search(r'<section\b[^>]*\bid="'+re.escape(sid)+r'"[^>]*>.*?</section>',original,re.S)
        assert match, sid
        content=match.group(0)
        content=content.replace('href="#review"','href="methods.html#review"')
        return content

    def src(sid, label=None):
        s=source_map[sid]
        return external(s['url'], label or s['title'])

    def heading(kicker,title,deck,aside='FY2023–FY2026',extra=''):
        return f'<div class="page-intro wrap"><div class="eyebrow-line"><span>{esc(kicker)}</span><span>{esc(aside)}</span></div><h1 id="content" tabindex="-1">{title}</h1><p class="deck">{deck}</p>{extra}</div>'

    def shell(filename,title,body,active='',depth=0,description=None):
        prefix='../'*depth
        body=compact_headings(body)
        name_options=''.join('<option value="'+esc(p['name'],quote=True)+'"></option>' for p in sorted(people,key=lambda p:p['name'].casefold()))
        name_search=f'<search class="site-search" data-site-search hidden aria-label="Site names"><form action="{prefix}individual-benefits.html#directory" method="get"><label for="site-name-search">Search names</label><input id="site-name-search" name="q" type="search" placeholder="Name or company" list="name-options" autocomplete="off" autocapitalize="none" autocorrect="off" spellcheck="false" enterkeyhint="search"><button type="submit">Search</button><datalist id="name-options">{name_options}</datalist></form></search>'
        if filename == 'individual-benefits.html':
            name_search = ''
        links=''.join(f'<a href="{prefix}{url}"'+(' aria-current="page"' if url==active else '')+f'>{label}</a>' for url,label in FILES)
        desc=description or 'Follow federal spending, named people, compensation, ownership and the gaps in the public record. Primary sources and dated evidence.'
        html=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="{esc(desc,quote=True)}"><meta name="theme-color" content="#0d1413"><meta name="color-scheme" content="dark"><title>{esc(title)} · SignalGraph</title><link rel="icon" href="{prefix}assets/signalgraph-mark.svg" type="image/svg+xml"><link rel="preload" href="{prefix}assets/lora-regular.ttf" as="font" type="font/ttf" crossorigin><link rel="preload" href="{prefix}assets/nunito-sans-regular.ttf" as="font" type="font/ttf" crossorigin><link rel="stylesheet" href="{prefix}assets/base.css"><link rel="stylesheet" href="{prefix}assets/pages.css"><link rel="stylesheet" href="{prefix}assets/theme.css"><link rel="stylesheet" href="{prefix}assets/directory.css"><script src="{prefix}assets/pages.js" defer></script></head><body><a class="skip" href="#content">Skip to the content</a><header class="topbar"><div class="wrap toprow"><a class="brand" href="{prefix}index.html" aria-label="SignalGraph home"><img class="brandmark" src="{prefix}assets/signalgraph-mark.svg" alt="" width="49" height="46">SignalGraph</a><nav class="nav" aria-label="Primary">{links}</nav>{name_search}</div><div class="reading-line" aria-hidden="true"></div></header><main>{body}</main><footer><div class="wrap footer-row"><span><strong>SignalGraph</strong> · Follow the money</span><nav class="foot-nav" aria-label="Footer"><a href="{prefix}methods.html">Evidence</a><a href="{prefix}blind-spots.html">Blind Spots</a></nav><span>Evidence reviewed November 12, 2026</span></div></footer></body></html>'''
        html=re.sub(r'(assets/(?:base|pages|theme|directory)\.(?:css|js))"',lambda match: match[1]+'?v='+asset_revision+'"',html)
        path=dist/filename;path.parent.mkdir(exist_ok=True,parents=True);path.write_text(html)

    def spotlight(p):
        return next((m for m in p['measurements'] if m['kind']=='equity'), next(iter(p['measurements']),None))

    def person_card(p):
        metric=spotlight(p)
        value=money(metric['amount']) if metric else 'Unpriced'
        label=metric['label'] if metric else 'Ownership or leadership connection'
        period=metric['period'] if metric else 'Personal proceeds have not been established'
        search=' '.join([p['name'],p['company'],p['role'],p.get('aliases','')]).lower()
        return f'''<article class="person-card {'unquantified' if not p['qualifies'] else ''}" data-person="{p['id']}" data-search="{esc(search,quote=True)}" data-company-name="{esc(p['company'],quote=True)}" data-category="{'documented' if p['qualifies'] else 'unquantified'}"><div class="company">{esc(p['company'])}</div><h3><a href="people/{p['slug']}.html">{esc(p['name'])}</a></h3><p class="role">{esc(p['role'])}</p><div class="person-value">{value}</div><p class="measure">{esc(label)}</p><p class="period">{esc(period)}</p><a class="card-link" href="people/{p['slug']}.html">Profile <span aria-hidden="true">→</span></a></article>'''

    def rank_chart(kind):
        rows=[]
        for p in people:
            metrics=[m for m in p['measurements'] if m['kind']==kind and m['amount']>=THRESHOLD]
            if metrics:
                m=max(metrics,key=lambda x:x['amount']);rows.append((p,m))
        rows=sorted(rows,key=lambda x:x[1]['amount'],reverse=True)[:5]
        ceiling=rows[0][1]['amount']
        return '<ol class="rank-list">'+''.join(f'<li><div class="rank-meta"><a href="people/{p["slug"]}.html">{esc(p["name"])}</a><strong>{money(m["amount"])}</strong></div><small>{esc(p["company"])} · {esc(m["period"])}</small><div class="rank-line" aria-hidden="true"><span style="--value:{100*m["amount"]/ceiling:.4f}%"></span></div></li>' for p,m in rows)+'</ol>'

    # The overview deliberately points into two substantial branches.
    home=heading('Following public money','Public spending.<br><em>Private benefit.</em>','Follow the money into companies, then examine the people, ownership structures and financial rewards behind them.',extra='<div class="journey"><span>Public agencies</span><i aria-hidden="true">→</i><span>Recipient companies</span><i aria-hidden="true">→</i><span>People &amp; owners</span></div>')
    home+=f'''<div class="wrap"><div class="landing-grid"><article class="landing-card"><span class="eyebrow">01 · The public ledger</span><h2>Government<br>spending</h2><div><div class="landing-number">{money(total)}</div><p class="landing-caption">Reported net federal contract obligations across four fiscal years. FY2026 remains incomplete.</p></div><div class="mini-bars" aria-hidden="true"><span style="height:88%"><b>2023</b></span><span style="height:87%"><b>2024</b></span><span style="height:98%"><b>2025</b></span><span class="tentative" style="height:94%"><b>2026</b></span></div><p>Four years of recipient records, the companies named in the research, payment errors and unresolved oversight findings.</p><a class="action-link" href="government-spending.html">Explore government spending <span aria-hidden="true">→</span></a></article><article class="landing-card people-landing"><span class="eyebrow">02 · The people behind it</span><h2>Individual<br>benefits</h2><div><div class="landing-number">{len(people)}<span style="font:400 1.3rem var(--sans);letter-spacing:0"> entries</span></div><p class="landing-caption">Executives, owners and family groups linked to the companies in the spending index.</p></div><p>Compensation, equity and share-sale disclosures of $50,000 or more. Separate profiles for owners whose personal proceeds remain unresolved.</p><p class="small-note">{len(qualified)} have a qualifying documented financial measure. {len(unknown)} have unquantified ownership or leadership connections.</p><a class="action-link" href="individual-benefits.html">Meet the people <span aria-hidden="true">→</span></a></article></div><div class="insight-band"><h2>The most revealing gaps<br>are in the connections.</h2><div><p>A company award, an executive pay package and an owner’s proceeds answer different questions. Each page shows what the record establishes and what remains missing.</p><p><a href="blind-spots.html">Explore the open questions →</a></p></div></div></div>'''
    home=re.sub(r'<div class="mini-bars" aria-hidden="true">.*?</div>', '<div class="mini-bars" aria-hidden="true">'+home_bars+'</div>',home,flags=re.S)
    home+='<section class="wrap research-download"><span class="eyebrow">New evidence · November 2026 review</span><h2>What happens when the funding safeguards change?</h2><p>GAO documents changes to Intel’s CHIPS milestones and payment terms. New profiles also connect pharmaceutical distribution, construction and property leases to the people behind those companies.</p><a class="action-link" href="government-spending.html#spending-channels">Follow the newly examined routes →</a><p class="reconciliation-notice"><a href="reconciliation.html">Read the evidence review →</a></p></section>'
    shell('index.html','Accountability',home)

    # Government page: retain the audited case narratives and expand the raw record view.
    government=heading('The public ledger','Government spending.<br><em>Follow every layer.</em>','Explore four fiscal years of federal contracts, the recipient companies named in the report, and the oversight findings that deserve follow-up.',extra='<nav class="jump-links" aria-label="Government spending sections"><a href="#recipients">Contract totals</a><a href="#annual-records">Four-year recipient records</a><a href="#spending-channels">New spending routes</a><a href="#companies">Company index</a><a href="#payments">Payment errors</a><a href="#medicaid">State audits</a><a href="#defense">Defense audits</a></nav>')
    government+='''<div class="wrap"><div class="metric-grid"><article class="metric-box"><span class="eyebrow">Federal outlays · FY2023–FY2026</span><div class="big-number">$27.27<span>T</span></div><h2>The broader spending universe</h2><p class="small-note">CBO’s four annual outlay totals cover benefits, interest, grants, procurement and other federal spending. These cash outlays are a different measure from contract commitments.</p>'''+external('https://www.cbo.gov/publication/61986','CBO November 2026 budget review')+'''</article><article class="metric-box warm"><span class="eyebrow">A dated contract snapshot</span><div class="big-number">$3.17<span>T</span></div><h2>Commitments to suppliers</h2><p class="small-note">Net obligations recorded for FY2023–FY2026 contract transactions, including negative adjustments. Do not subtract these from outlays or treat them as personal income.</p><a class="source-link" href="spending-snapshot.json" download>Download the exact queries and responses ↓</a></article></div></div>'''
    recipient_section=section('recipients').replace('<b>01</b>','<b>01</b>',1)
    government+=recipient_section
    government+='''<section class="content-section wrap" id="annual-records"><div class="section-head"><h2>More of the recipient record.</h2><p>The ten largest recipient records in each annual query. A record is identified by UEI; matching corporate names can still represent different records.</p></div><p class="small-note">These 40 annual observations are reproduced from the November 12 snapshot. Rank is within each year’s query. Missing from a top-ten list does not mean zero awards.</p>'''
    for year,bundle in review['spending']['recipients'].items():
        rows=bundle['response']['results']
        government+=f'<details class="year-records" {"open" if year=="2025" else ""}><summary>FY{year} · Ten recipient records'+(' · Reporting incomplete' if year=='2026' else '')+'</summary><div class="table-scroll" role="region" tabindex="0" aria-label="FY'+year+' recipient records"><table class="records-table"><caption>FY'+year+' · Net contract obligations</caption><thead><tr><th scope="col">Rank / recipient</th><th scope="col">UEI</th><th scope="col">Net obligations</th></tr></thead><tbody>'
        for rank,row in enumerate(rows,1):
            government+=f'<tr><th scope="row">{rank:02} · {esc(row["name"].title())}</th><td>{esc(row["uei"] or "Not supplied")}</td><td class="money">${row["amount"]:,.2f}</td></tr>'
        government+='</tbody></table></div></details>'
    government+='</section>'
    government+=channels(reconciliation,people,source_map)
    government+=f'<section class="content-section wrap" id="companies"><div class="section-head"><h2>The company index.</h2><p>{len(companies["companies"])} named companies across the recipient sheets and people analysis, including the Pfizer/PIP identifier collision. Linked people lead to their individual evidence pages.</p></div><p class="small-note">This is an index of the research’s named entities. Conflicting report totals are withheld; it is not a consolidated ranking of all contractors.</p><search aria-label="Companies"><form class="filters company-filters" data-company-filters hidden><div><label for="company-search">Search companies</label><div class="filter-search"><input id="company-search" name="company" type="search" placeholder="Company or beneficiary" autocomplete="off" autocapitalize="none" autocorrect="off" spellcheck="false"><button class="clear-search" data-company-clear type="button" hidden>Clear</button></div></div></form></search><p class="results-count" id="company-count" role="status" aria-atomic="true">{len(companies["companies"])} companies shown</p><div class="recipient-directory">'
    for c in companies['companies']:
        linked=[p for p in people if c['id'] in p['company_ids']]
        company_search=' '.join([c['name']]+[p['name'] for p in linked])
        government+=f'<article class="recipient-entry" data-company data-search="{esc(company_search,quote=True)}" id="company-{c["slug"]}"><h3>{esc(c["name"])}</h3><p>{esc(c["note"])}</p>'
        government+=''.join(f'<a href="people/{p["slug"]}.html">{esc(p["name"])}</a>' for p in linked)
        if c.get('source_ids'):
            government+='<details><summary>Company evidence</summary>'+''.join(src(s) for s in c['source_ids'])+'</details>'
        if not linked:government+='<p class="company-marker">No named individual in the supplied people analysis. A research lead, not a finding of no personal beneficiaries.</p>'
        government+='</article>'
    government+='</div><p class="no-results" id="company-empty" hidden>No matching companies. Try another name.</p></section>'
    for number,sid in enumerate(['payments','medicaid','defense','contracts','questions'],2):
        part=section(sid)
        part=re.sub(r'(<div class="section-no"><b>)\d+(</b>)',lambda m:m[1]+f'{number:02}'+m[2],part,count=1)
        government+=part
    government+='<div class="wrap research-download"><h2>Who benefits behind these companies?</h2><p>Open the individual profiles for compensation, equity disclosures, ownership relationships and unresolved personal proceeds.</p><a class="action-link" href="individual-benefits.html">Explore individual benefits →</a></div>'
    shell('government-spending.html','Government spending',government,'government-spending.html')

    benefits='<div class="wrap directory-intro"><div class="directory-title"><h1 id="content" tabindex="-1">Beneficiaries</h1><span>FY2023–FY2026</span></div><p class="deck">Compensation, equity and ownership, with sources.</p></div>'
    comparisons='<section class="content-section wrap" id="comparisons"><div class="section-head"><h2>Compare like with like.</h2><p>These are the largest verified values in this selected report cohort. Each comparison uses one measure. Figures are not a government-paid personal-income ranking.</p></div><div class="metric-grid"><article class="metric-box warm"><span class="eyebrow">Equity vesting &amp; option exercise</span><h3>Value when equity becomes available</h3>'+rank_chart('equity')+'<p class="small-note">2025 gross vesting value plus exercise spread, before taxes. Stock sales are a separate event; adding them could count the same shares twice.</p></article><article class="metric-box"><span class="eyebrow">Reported compensation</span><h3>Annual pay-package disclosures</h3>'+rank_chart('compensation')+'<p class="small-note">Summary Compensation Table totals include grant-date values and can include awards later forfeited. Issuer fiscal-year labels are shown; these are not all cash received.</p></article></div></section>'
    comparisons+=transactions(reconciliation,source_map)
    benefits+=render_directory(people,person_card,THRESHOLD)
    benefits+=comparisons
    benefits+='<div class="wrap research-download"><h2>What could change these profiles?</h2><p>Ownership records, complete stock-sale histories, private distributions, and personal allocation evidence could materially change the findings.</p><a class="action-link" href="blind-spots.html">See the next research questions →</a></div>'
    shell('individual-benefits.html','Beneficiaries',benefits,'individual-benefits.html')

    # Individual pages keep metric definitions, dates and limitations immediately alongside values.
    for p in people:
        metric=spotlight(p)
        crumb=f'<nav class="profile-breadcrumbs wrap" aria-label="Breadcrumbs"><ol><li><a href="../index.html">Home</a></li><li><a href="../individual-benefits.html">Individual benefits</a></li><li><a href="{p["slug"]}.html" aria-current="page">{esc(p["name"])}</a></li></ol></nav>'
        body=crumb+'<div class="wrap"><div class="profile-layout"><div class="profile-lead">'
        body+=f'<div class="page-intro"><span class="eyebrow">{esc(p["company"])}</span><h1 id="content" tabindex="-1">{esc(p["name"])}</h1><p class="role">{esc(p["role"])}</p><p class="small-note">Roles and financial disclosures are dated to the cited records. They are not a determination of wrongdoing.</p></div></div><aside class="profile-spotlight"><span class="eyebrow">{esc(metric["period"]) if metric else "Personal benefit · Evidence gap"}</span><div class="profile-number">{money(metric["amount"]) if metric else "Unquantified"}</div><p class="metric-name">{esc(metric["label"]) if metric else "Personal proceeds have not been established"}</p><p class="small-note">{esc(metric["note"]) if metric else "The report names this person or family. The available evidence does not establish a qualifying personal amount; unknown is not zero."}</p>'
        if metric:body+=src(metric['source_id'])
        body+='</aside></div>'
        company=next(c for c in companies['companies'] if c['id']==p['company_ids'][0])
        body+=f'<div class="profile-route"><div><span class="eyebrow">Company tracked in the report</span><strong>{esc(p["company"])}</strong><a class="source-link" href="../government-spending.html#company-{company["slug"]}">View the company index →</a></div><span class="arrow" aria-hidden="true">→</span><div><span class="eyebrow">Documented relationship</span><strong>{esc(p["relationship"])}</strong><p class="small-note">Company obligations are not this person’s income.</p></div></div>'
        body+='<div class="profile-detail-grid"><div><h2>What the record shows.</h2>'
        if p.get('ownership'):
            o=p['ownership'];body+=f'<div class="inline-note"><strong>{esc(o["headline"])}</strong><p>{esc(o["detail"])}</p>{src(o["source_id"])}</div>'
        for m in p['measurements']:
            body+=f'<article class="method-block"><h3>{esc(m["label"])}</h3><p class="data-window">{esc(m["label"])} · {esc(m["period"])}</p><p><strong>${m["amount"]:,.0f}</strong></p><p class="small-note">{esc(m["note"])}</p>'
            if m.get('components'):
                body+='<div class="table-scroll" role="region" tabindex="0" aria-label="Metric components"><table class="records-table"><caption>Components of this measure</caption><thead><tr><th scope="col">Component</th><th scope="col">Value</th></tr></thead><tbody>'
                body+=''.join(f'<tr><th scope="row">{esc(label)}</th><td class="money">${value:,.0f}</td></tr>' for label,value in m['components'])
                body+='</tbody></table></div>'
            body+=src(m['source_id'])+'</article>'
        if p.get('history'):
            body+='<div class="table-scroll" role="region" tabindex="0" aria-label="Earlier compensation disclosures"><table class="records-table"><caption>Compensation history available in the cited table</caption><thead><tr><th scope="col">Issuer fiscal year</th><th scope="col">SCT total</th></tr></thead><tbody>'
            body+=''.join(f'<tr><th scope="row">{esc(str(y))}</th><td class="money">${v:,.0f}</td></tr>' for y,v in sorted(p['history'].items()))
            body+='</tbody></table></div><p class="small-note">Years not shown have not been verified here. These disclosures are not a complete four-year personal cash-flow total.</p>'
        if not p['measurements'] and not p.get('ownership'):body+='<p>The cited records establish the relationship described above. Personal compensation, distributions, ownership percentages and liquidity proceeds remain unresolved.</p>'
        if p['notes']:body+='<ul class="fact-list">'+''.join(f'<li>{esc(note)}</li>' for note in p['notes'])+'</ul>'
        body+='</div><aside><h2>What is still missing.</h2><ul class="fact-list">'+''.join(f'<li>{esc(q)}</li>' for q in p['unknowns'])+'</ul><div class="evidence-note"><p>Government-attributed personal income is unverified. A company’s government-revenue share does not establish which dollars funded an individual’s compensation or gains.</p></div><h2>Sources for this profile.</h2><ul class="supporting-sources">'
        for sid in dict.fromkeys(p['source_ids']):
            s=source_map[sid];body+='<li>'+src(sid)+'<small>'+esc('; '.join(s.get('locators',[])))+'</small></li>'
        body+='</ul><p class="small-note">Research locator: '+esc('; '.join(p['input_locators']))+'</p></aside></div><div class="profile-next"><a href="../individual-benefits.html#directory">← All individual profiles</a><a href="../blind-spots.html">Blind spots &amp; research questions →</a><a href="../people-evidence.json" download>Download profile evidence ↓</a></div></div><div style="height:45px"></div>'
        shell('people/'+p['slug']+'.html',p['name'],body,'individual-benefits.html',1)

    known=[
      ('Who ultimately owns the recipient?','Private stakes, trust interests and investment-fund allocations are not consistently disclosed. Longview’s advisory position does not allocate all shares to the Crown family.','Dated ownership records, capital tables, share classes, trust disclosures and actual economic interests.'),
      ('What did the individual actually receive?','A grant-date award, vesting value, option gain and later sale can refer to the same shares. A report estimate is not a documented distribution.','Transaction-level equity reconciliation, cash distributions, tax withholding, exercise costs and clawbacks.'),
      ('Are corporate groups resolved correctly?','Multiple UEIs, subsidiaries, mergers and joint ventures can split one group or cause overlapping totals. The supplied sheets also disagree on entity identities.','Time-aware parent and subsidiary links, joint-venture ownership and transaction IDs.'),
      ('Where is the rest of the four-year history?','The spending query spans FY2023–FY2026. Many personal disclosures cover only 2025; company fiscal years and federal fiscal years are different calendars.','2023–2026 issuer filings, compensation histories, dated transactions and explicit uncovered periods.'),
      ('What passes through to other recipients?','Prime awards can fund subcontractors, manufacturers, medical providers and lenders. The prime recipient may retain only a portion.','Subawards, supplier disclosures, managed-care payments, subcontractor records and retained-fee evidence.'),
      ('What is absent from the source systems?','Defense procurement reporting is delayed. State programs, tax benefits, subsidies and some agreements require other sources. The federal contract query is only one part of government spending.','Reconciled agency totals, state portals, program-specific records and refreshes after reporting delays.'),
    ]
    unexplored=[
      ('Trace political and family financial interests.','Politicians and publicly documented extended-family business interests may connect to recipients through companies, trusts, leases, employment or investment vehicles.','Verify kinship, economic interest, dates and any official decision authority separately; a family link alone does not establish a benefit or misconduct.'),
      ('Look beyond the report’s selected sectors.','Screen high-dollar spending categories for names absent from the report: property leases, IT resellers, disaster contracting, loan guarantees, logistics and infrastructure.','Use agency/category concentration to choose searches before looking for familiar individuals.'),
      ('Find the second and third ownership layers.','A recipient may be controlled through a holding company, a private fund, a trust or an acquisition. Different layers can share costs and returns.','Follow dated legal entities until economic ownership is supported or the trail becomes explicitly unresolved.'),
      ('Search for people hidden by timing.','An executive can change employers; a founder can sell before a large award; a private sponsor can exit after years of contracts.','Compare appointments, acquisitions, divestitures and equity transactions against the award timeline.'),
      ('Test the places where coverage looks complete.','Repeated control totals, unchanged ownership percentages, missing negative adjustments or neat round values can conceal acquisition and modeling errors.','Use reconciliation tests and counterexamples; document failed searches and unresolved discrepancies.'),
    ]
    def gaps(rows):
        return '<div class="blindspot-list">'+''.join(f'<article class="blindspot"><span class="gap-index">{i:02}</span><h3>{esc(title)}</h3><p>{esc(detail)}</p><p class="next-evidence"><strong>Next evidence:</strong> {esc(next_step)}</p></article>' for i,(title,detail,next_step) in enumerate(rows,1))+'</div>'
    blind=heading('The next investigation','The gaps are<br><em>part of the story.</em>','Some evidence is missing. Other beneficiaries and spending routes may not yet have been identified. Both belong on the research agenda.')
    blind+=section('visibility').replace('<b>03</b>','<b>01</b>',1)
    blind+='<section class="content-section wrap"><div class="section-head"><h2>Known blind spots.</h2><p>Specific questions the current evidence cannot answer.</p></div>'+gaps(known)+'</section>'
    blind+='<section class="unknown-field"><div class="wrap"><h2>What have we not<br>thought to look for?</h2><p class="small-note">Questions about ownership, timing and spending channels that the current evidence does not resolve.</p>'+gaps(unexplored)+'</div></section>'
    blind+=followups(reconciliation)
    shell('blind-spots.html','Blind spots & next research',blind,'blind-spots.html')

    methods=heading('Follow the records','Evidence that<br><em>can be checked.</em>','How the site separates government commitments, company disclosures, personal proceeds and unresolved ownership.')
    methods+='<div class="wrap"><section class="method-block" id="inclusion"><h2>Inclusion</h2><p>A financial entry qualifies if at least one verified compensation, equity or share-sale measure is $50,000 or more in its stated period within the research window. This is not a claim that at least $50,000 was personally paid by taxpayers. All named ownership connections remain indexed when personal amounts are unknown.</p></section><section class="method-block"><h2>Every name is represented. Every amount still needs evidence.</h2><p>The directory covers selected executives, owners and family groups connected to the companies in the spending index. Each profile links to dated disclosures and identifies unresolved amounts. Coverage is selective and continues to expand.</p></section><section class="method-block"><h2>Four fiscal years, several reporting calendars.</h2><p>Contract transactions run October 1, 2022 through September 30, 2026. Issuer compensation and equity tables retain their own fiscal-year labels. FY2026 procurement reporting is incomplete in this November 12 snapshot. A missing year is not zero.</p></section><section class="method-block"><h2>Keep the measures separate.</h2><p>Contract obligations are commitments. Company revenue is recognized as work is performed. Summary Compensation Table totals include grant-date fair values. Vesting and exercise values are not net sale cash. Ownership and voting rights are stocks and rights, not income flows. Gross share sales are a separate event; trust or client-account transactions are not fully allocated to a named individual without economic-interest evidence. None of these values are added together as a single personal taxpayer-benefit total.</p></section><section class="method-block"><h2>Forfeitures and employer changes matter.</h2><p>Jesus Malave has separate 2025 disclosures at Lockheed Martin and Boeing; the Lockheed figure includes grant-date awards later forfeited. Andrew Witty’s disclosure also needs forfeiture context. Profiles preserve these qualifications instead of presenting the totals as cash received.</p></section><div class="downloads"><a href="people-evidence.json" download>Profile evidence</a><a href="spending-snapshot.json" download>Spending queries &amp; responses</a><a href="audit-findings.txt" download>Audit findings</a><a href="reconciliation.html">Reconciliation review</a><a href="relationships.json" download>Relationship graph</a><button data-print type="button">Print this page</button></div></div>'
    methods+='<div class="wrap research-download"><h2>The reconciliation was audited, too.</h2><p>Corrections to financial totals, identities and reporting periods, with links to the supporting records.</p><a class="action-link" href="reconciliation.html">See the reconciliation audit →</a></div>'
    methods+=section('review')
    methods+='<section class="sources wrap" id="sources"><h2>Primary sources.</h2><p class="sources-intro">Citations link directly to the record. Some source documents support more than one profile or measurement.</p><ol class="source-list">'
    all_sources=[{'title':s['title'],'url':s['url'],'locators':[s.get('locator','')]} for s in evidence['sources']]+list(source_map.values())
    seen=set();unique=[]
    for s in all_sources:
        if s['url'] not in seen:seen.add(s['url']);unique.append(s)
    for i,s in enumerate(unique,1):methods+=f'<li><span class="source-num">{i:02}</span><div>'+external(s['url'],s['title'])+'<p>'+esc('; '.join(s.get('locators',[])))+'</p></div></li>'
    methods+='</ol></section>'
    shell('methods.html','Sources & method',methods,'methods.html')
    audit_body=heading('Review of the new evidence','What survived<br><em>the source check.</em>','Supported additions, corrected claims and remaining gaps from the November 2026 reconciliation.')
    shell('reconciliation.html','Reconciliation audit',audit_body+audit(reconciliation,source_map),'methods.html')
    evidence['expanded_directory']={'profile_count':len(people),'qualifying_documented_entries':len(qualified),'unquantified_entries':len(unknown),'threshold_usd':THRESHOLD,'evidence_file':'people-evidence.json','company_index_file':'company-index.json'}
    (dist/'evidence.json').write_text(json.dumps(evidence,indent=2,ensure_ascii=False))
    result={'html_pages':len(list(dist.rglob('*.html'))),'profile_count':len(people),'qualifying_documented':len(qualified),'unquantified':len(unknown),'companies':len(companies['companies']),'primary_sources':len(unique)}
    (dist/'edition.json').write_text(json.dumps(result,indent=2))
    with (dist/'audit-findings.txt').open('a') as notes:
        notes.write(f'\n\nRECONCILIATION REVIEW — NOVEMBER 2026\n{len(people)} selected profiles; {len(qualified)} qualify on a documented financial measure; {len(unknown)} remain unquantified. Threshold: $50,000 in the stated period, not established taxpayer receipts.\n')
        for change in reconciliation['site_changes']:
            notes.write(change['id']+' — '+change['status']+'\n'+change['decision']+'\nStill needed: '+change['remaining']+'\n\n')
        notes.write('Additional corrections:\n'+'\n'.join(reconciliation['additional_findings'])+'\n')

    print(json.dumps(result))
