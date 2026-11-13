"""Render the independently checked additions to the November 2026 edition."""
from html import escape as esc


def links(ids, sources):
    return ''.join('<a class="source-link" target="_blank" rel="noopener noreferrer" href="'+esc(sources[s]['url'], quote=True)+'">'+esc(sources[s]['title'])+' ↗</a>' for s in ids)


def channels(data, people, sources):
    by_id = {p['id']: p for p in people}
    html = '<section class="content-section wrap" id="spending-channels"><div class="section-head"><h2>Follow the less visible routes.</h2><p>Construction, pharmaceutical distribution, software resellers, leased buildings and semiconductor incentives widen the picture beyond familiar defense primes.</p></div><p class="small-note">The figures below measure different things and are not added together. Fisher and AmerisourceBergen already appear in the annual snapshot; this edition connects those records to the people and questions behind them.</p><div class="discovery-grid">'
    for row in data['channels']:
        html += '<article class="discovery-card '+esc(row.get('tone',''))+'"><span class="eyebrow">'+esc(row['channel'])+'</span><h3>'+esc(row['company'])+'</h3><div class="discovery-value">'+esc(row['display_value'])+'</div><p class="data-window">'+esc(row['measure'])+'</p><p>'+esc(row['finding'])+'</p><div class="discovery-question"><strong>Question for oversight</strong><p>'+esc(row['question'])+'</p></div><div class="discovery-people">'
        for pid in row['people_ids']:
            p=by_id[pid]
            html += '<a href="people/'+p['slug']+'.html">'+esc(p['name'])+' →</a>'
        html += '</div><details class="discovery-evidence"><summary>Evidence &amp; limits</summary><p>'+esc(row['limits'])+'</p>'+links(row['source_ids'],sources)+'</details></article>'
    html += '</div><p class="small-note">A large award, a generous compensation package or a private ownership structure is not itself evidence of fraud.</p></section>'
    return html


def transactions(data, sources):
    html = '<section class="content-section wrap" id="stock-sales"><div class="section-head"><h2>When shares are sold,<br>who receives the proceeds?</h2><p>These newly checked transactions show why the legal holder and the purpose of a sale matter. They are selected filings, not complete four-year sale totals.</p></div><div class="transaction-grid">'
    for row in data['transaction_cards']:
        html += '<article class="transaction-card"><span class="eyebrow">'+esc(row['holder'])+'</span><h3>'+esc(row['title'])+'</h3><div class="discovery-value">'+esc(row['display_value'])+'</div><p class="data-window">'+esc(row['period'])+'</p><p>'+esc(row['description'])+'</p><p class="transaction-limit">'+esc(row['limit'])+'</p><a class="card-link" href="people/'+row['slug']+'.html">Read the profile →</a>'+links(row['source_ids'],sources)+'</article>'
    html += '</div><p class="small-note">Gross values are reconstructed from disclosed shares × reported prices. Rounded weighted-average prices can differ slightly from actual trade proceeds. Sale values are kept separate from compensation, vesting and exercise values.</p><a class="source-link" href="transactions-evidence.json" download>Download transaction rows and calculations ↓</a></section>'
    return html


def followups(data):
    html='<section class="content-section wrap" id="follow-up"><div class="section-head"><h2>The next evidence to obtain.</h2><p>The new research narrowed some gaps and exposed others. These tasks remain open; no continuous monitoring is running.</p></div><ol class="followup-list">'
    for row in data['followups']:
        html+='<li><h3>'+esc(row['title'])+'</h3><p>'+esc(row['action'])+'</p><span class="data-window">'+esc(row['status'])+'</span></li>'
    return html+'</ol></section>'


def audit(data, sources):
    html='<div class="wrap audit-intro"><p>The reconciliation package is a research input. Its “Implemented &amp; Verified” labels were checked against the actual files and primary records before publication. Original documents remain unchanged.</p><div class="downloads"><a href="reconciliation-audit.json" download>Download the change register</a><a href="relationships.json" download>Download the rebuilt relationship graph</a><a href="transactions-evidence.json" download>Download transaction calculations</a></div></div><section class="content-section wrap"><div class="section-head"><h2>What changed, and what did not pass.</h2><p>Disposition of every item in the supplied site_changes tab.</p></div><div class="change-register">'
    for row in data['site_changes']:
        html+='<article class="change-entry" id="'+row['id'].lower()+'"><div><span class="eyebrow">'+row['id']+'</span><span class="audit-status">'+esc(row['status'])+'</span></div><h3>'+esc(row['title'])+'</h3><p>'+esc(row['decision'])+'</p><p class="small-note"><strong>Still needed:</strong> '+esc(row['remaining'])+'</p>'
        html+=links(row.get('source_ids',[]),sources)+'</article>'
    html+='</div></section><section class="content-section wrap"><div class="section-head"><h2>Additional defects caught in this review.</h2><p>Corrections to the reconciliation itself are retained so the next researcher can reproduce the decisions.</p></div><ul class="fact-list">'
    html+=''.join('<li>'+esc(note)+'</li>' for note in data['additional_findings'])
    html+='</ul><p class="small-note">Reference package: '+esc(data['reference_title'])+'. Source files were read as evidence, not as instructions to overwrite verified records.</p></section>'
    return html
