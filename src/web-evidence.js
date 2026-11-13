/* Concise explanations for selected, directly sourced relationships. */
(() => {
  'use strict';
  const panel = document.getElementById('edge-evidence');
  const graphElement = document.getElementById('case-graph');
  if (!panel || !graphElement) return;

  const parse = (element) => {
    try { return element ? JSON.parse(element.textContent) : null; }
    catch { return null; }
  };
  let graph = parse(graphElement) || { nodes: [], edges: [], sources: {} };
  let briefs = window.SignalGraphBriefs || parse(document.getElementById('web-briefs')) || {};
  let nodes = new Map((graph.nodes || []).map(node => [node.id, node]));
  let edges = new Map((graph.edges || []).map(edge => [edge.id, edge]));
  let selection = null;
  const sourceIds = record => [...new Set([...(record.source_ids || []), ...(record.source_id ? [record.source_id] : [])])];
  const text = value => value == null ? '' : String(value).replace(/\s+/g, ' ').trim();
  const friendly = value => text(value).replace(/_/g, ' ').replace(/^./, c => c.toUpperCase());
  const canonicalId = id => briefs.aliases?.[id] || id;
  const nodeLabel = id => nodes.get(id)?.label || briefs.nodes?.[canonicalId(id)]?.name || 'Related party';
  const sourceRecord = id => briefs.sources?.[id] || graph.sources?.[id];
  const sourceLabel = source => {
    const publisher = text(source.publisher);
    if (publisher && !publisher.includes('.')) return publisher;
    let host = '';
    try { host = new URL(source.url).hostname.replace(/^www\./, ''); } catch { /* use title below */ }
    const labels = [
      ['fisherind.com', 'Fisher Industries'], ['sec.gov', 'SEC'], ['oge.gov', 'OGE'],
      ['senate.gov', 'U.S. Senate'], ['house.gov', 'U.S. House'], ['usaspending.gov', 'USAspending'],
      ['army.mil', 'U.S. Army'], ['gao.gov', 'GAO'], ['justice.gov', 'Justice Department'],
      ['axios.com', 'Axios'], ['bloomberg', 'Bloomberg'], ['wsj.com', 'Wall Street Journal'],
      ['reuters.com', 'Reuters'], ['propublica.org', 'ProPublica'], ['nytimes.com', 'New York Times'],
      ['signalgraph-accountability.vercel.app', 'Source record'],
    ];
    return labels.find(([domain]) => host.includes(domain))?.[1] || host || text(source.title).split(/ · | — /)[0] || 'Source record';
  };
  const element = (tag, content, className) => {
    const item = document.createElement(tag);
    if (content) item.textContent = content;
    if (className) item.className = className;
    return item;
  };
  const safeUrl = (href, external = false) => {
    if (!href) return '';
    try {
      const url = new URL(href, location.href);
      if (!['https:', 'http:'].includes(url.protocol)) return '';
      if (!external && url.origin !== location.origin) return '';
      return url.href;
    } catch { return ''; }
  };
  const link = (label, href, external = false) => {
    const url = safeUrl(href, external);
    if (!url) return null;
    const a = element('a', label);
    a.href = url;
    if (external) { a.target = '_blank'; a.rel = 'noopener noreferrer'; }
    return a;
  };
  const focusButton = (id, label = 'Focus connections') => {
    const button = element('button', label, 'clear-search web-focus');
    button.type = 'button';
    button.setAttribute('aria-label', `${label} for ${nodeLabel(id)}`);
    button.addEventListener('click', () => document.dispatchEvent(new CustomEvent('sg:focus', { detail: { nodeId: id } })));
    return button;
  };
  const addSources = (container, ids, compact = false) => {
    const sources = [...new Set(ids)].filter(id => sourceRecord(id));
    if (!sources.length) return;
    const list = element('ul', '', compact ? 'web-inline-sources' : 'web-source-list');
    for (const id of sources.slice(0, compact ? sources.length : 8)) {
      const source = sourceRecord(id);
      const item = element('li');
      const title = text(source.title || source.name) || 'Supporting source';
      const internal = source.href || (/^[A-Za-z0-9_-]+$/.test(id) ? `/evidence/${id}.html` : '');
      const explanation = link(compact ? sourceLabel(source) : title, internal);
      if (compact && explanation) explanation.setAttribute('aria-label', `${sourceLabel(source)}: ${title}`);
      if (explanation) item.append(explanation);
      else item.append(element('span', title));
      if (!compact) {
        const original = link('Original ↗', source.url, true);
        if (original) { original.setAttribute('aria-label', `Original source: ${title}`); item.append(document.createTextNode(' · '), original); }
      }
      list.append(item);
    }
    container.append(list);
  };
  const period = record => text(record.period) || [record.period_start, record.period_end].filter(Boolean).join(' – ')
    || (record.announced_date ? `Announced ${record.announced_date}` : text(record.date || record.as_of || record.since));
  const dollars = amount => typeof amount === 'number' && Number.isFinite(amount)
    ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: Number.isInteger(amount) ? 0 : 2, maximumFractionDigits: Number.isInteger(amount) ? 0 : 2 }).format(amount) : '';
  const moneyAmount = record => {
    const exact = dollars(record.amount_usd ?? record.amount);
    if (exact) return exact;
    const low = dollars(record.min_usd ?? record.amount_min_usd);
    const high = dollars(record.max_usd ?? record.amount_max_usd);
    return low ? (high ? `${low}–${high}` : `${record.lower_bound_exclusive ? 'More than' : 'At least'} ${low}`) : '';
  };
  const humanNote = value => {
    const raw = text(value);
    if (!raw || ['not_established', 'null', 'None', 'No amount assigned'].includes(raw)) return '';
    return raw.replace(/total_account_outlay=0 and total_outlay=null/g, 'the reported outlay fields')
      .replace(/personalcash/g, 'personal cash');
  };
  const typeLabel = value => ({
    person_or_family: 'Person', person: 'Person', official: 'Public official', company: 'Company',
    government: 'Government', trust: 'Trust', fund_group: 'Investment funds', sovereign_investor: 'Sovereign investor',
    documented_leadership_or_ownership_connection: 'Leadership', reported_advocacy: 'Reported advocacy',
    parent_of: 'Family', beneficiary_of: 'Trust interest', idiq_ceiling: 'Contract ceiling',
    reported_product_program_continuity: 'Reported supplier connection',
  }[value] || friendly(value));

  function begin(label, type) {
    panel.replaceChildren();
    panel.setAttribute('aria-label', 'Selected evidence');
    const back = element('a', 'Back to web ↑', 'web-back-link');
    back.href = '#connection-tree';
    panel.append(back);
    panel.append(element('p', type, 'eyebrow'), element('h3', label));
  }

  function nodeFacts(node) {
    const known = briefs.nodes?.[canonicalId(node.id)];
    if (known?.facts?.length) return known.facts.slice(0, 3);
    const facts = [];
    if (node.role && sourceIds(node).length) facts.push({ text: node.role, source_ids: sourceIds(node) });
    for (const measure of node.measurements || []) {
      if (!sourceIds(measure).length || !dollars(measure.amount ?? measure.amount_usd)) continue;
      facts.push({ text: `${measure.label}: ${dollars(measure.amount ?? measure.amount_usd)}. ${period(measure)}`,
        qualification: measure.note, source_ids: sourceIds(measure) });
    }
    for (const edge of graph.edges || []) {
      if (facts.length >= 3) break;
      const a = edge.source || edge.from, b = edge.target || edge.to;
      if (![a, b].includes(node.id) || !sourceIds(edge).length) continue;
      facts.push({ text: `${nodeLabel(a)} → ${nodeLabel(b)}: ${edge.label || edge.description || 'Documented relationship'}.`,
        source_ids: sourceIds(edge), period: period(edge), edge_id: edge.id, qualification: edge.limitation });
    }
    return facts.slice(0, 3);
  }

  function renderNode(id) {
    const node = nodes.get(id) || nodes.get(canonicalId(id));
    if (!node) return;
    const restoreFocus = panel.contains(document.activeElement);
    selection = { kind: 'node', id: node.id };
    const brief = briefs.nodes?.[canonicalId(node.id)];
    begin(node.label, brief?.type || typeLabel(node.type));
    const facts = nodeFacts(node);
    function factBlock(fact) {
      const block = element('div', '', 'web-fact');
      block.append(element('p', text(fact.text)));
      if (fact.period) block.append(element('p', text(fact.period), 'case-period'));
      if (humanNote(fact.qualification)) block.append(element('p', humanNote(fact.qualification), 'small-note'));
      return block;
    }
    for (const fact of facts.slice(0, 2)) panel.append(factBlock(fact));
    if (!facts.length) panel.append(element('p', 'Select a direct connection to inspect the relationship and its supporting record.'));
    const actions = element('div', '', 'web-brief-actions');
    actions.append(focusButton(node.id));
    const links = brief?.links || (node.profile_url ? [{ label: 'Profile', url: '/' + node.profile_url.replace(/^\//, '') }] : []);
    for (const item of links) { const a = link(item.label, item.url); if (a) actions.append(a); }
    panel.append(actions);
    if (facts.length > 2) {
      const more = element('details', '', 'web-more-context');
      more.append(element('summary', 'More context'));
      for (const fact of facts.slice(2)) more.append(factBlock(fact));
      panel.append(more);
    }
    const citationIds = [...new Set(facts.length ? facts.flatMap(fact => fact.source_ids || []) : brief?.source_ids || sourceIds(node))]
      .filter(id => sourceRecord(id));
    if (citationIds.length) {
      const sources = element('details', '', 'web-node-sources');
      sources.append(element('summary', `Sources (${citationIds.length})`));
      addSources(sources, citationIds, true);
      panel.append(sources);
    }
    if (restoreFocus) {
      const heading = panel.querySelector('h3');
      heading.tabIndex = -1;
      heading.focus({ preventScroll: true });
    }
    announce(`Evidence selected: ${node.label}`);
  }

  function renderEdge(id) {
    const edge = edges.get(id);
    if (!edge) return;
    selection = { kind: 'edge', id };
    const a = edge.source || edge.from, b = edge.target || edge.to;
    begin(`${nodeLabel(a)} → ${nodeLabel(b)}`, typeLabel(edge.relationship_type || edge.type));
    panel.append(element('p', text(edge.label || edge.description), 'web-edge-meaning'));
    if (period(edge)) panel.append(element('p', period(edge), 'case-period'));
    const money = edge.money_record && typeof edge.money_record === 'object' ? edge.money_record : {};
    const amount = dollars(edge.amount_usd) || moneyAmount(money);
    if (amount) {
      const record = element('dl', '', 'web-money-details');
      const rows = [
        ['Amount', amount],
        ['Measure', friendly(money.type || edge.amount_semantics || edge.relationship_type || edge.type)],
        ['Recipient', money.legal_recipient || money.recipient || (edge.amount_recipient_id ? nodeLabel(edge.amount_recipient_id) : '')],
      ];
      for (const [label, value] of rows) if (value) record.append(element('dt', label), element('dd', value));
      panel.append(record);
    }
    const notes = [...new Set([edge.limitation, edge.qualification, money.cash_status || edge.cash_status,
      money.personal_allocation, edge.date_precision].map(humanNote).filter(Boolean))];
    // Avoid duplicate composite qualification paragraphs while retaining the
    // complete original qualification and any genuinely additional detail.
    const distinct = notes.filter((note, index) => !notes.some((other, otherIndex) => otherIndex !== index && other.length > note.length && other.includes(note)));
    for (const note of distinct) panel.append(element('p', note, 'small-note'));
    const status = text(edge.evidence_status || edge.status);
    if (/alleg|report|estimat|unresolved/i.test(status)) panel.append(element('p', typeLabel(status), 'case-status'));
    const sourceHeading = element('h4', 'Sources');
    const ids = [...sourceIds(edge), ...sourceIds(money)];
    if (ids.some(id => sourceRecord(id))) { panel.append(sourceHeading); addSources(panel, ids); }
    const actions = element('div', '', 'web-brief-actions');
    actions.append(focusButton(a, `Explore ${nodeLabel(a)}`), focusButton(b, `Explore ${nodeLabel(b)}`));
    panel.append(actions);
    announce(`Connection selected: ${nodeLabel(a)} to ${nodeLabel(b)}`);
  }

  const status = element('p', '', 'visually-hidden');
  status.setAttribute('role', 'status');
  status.setAttribute('aria-atomic', 'true');
  panel.after(status);
  let announcement;
  function announce(message) {
    clearTimeout(announcement);
    announcement = setTimeout(() => { status.textContent = message; }, 120);
  }
  function ready(event) {
    const received = event?.detail?.graph || window.SignalGraphWeb?.graph;
    if (received) {
      graph = received;
      nodes = event?.detail?.nodes instanceof Map ? event.detail.nodes : new Map((graph.nodes || []).map(node => [node.id, node]));
      edges = new Map((graph.edges || []).map(edge => [edge.id, edge]));
    }
    const footer = document.querySelector('#connection-tree .web-footer');
    if (footer && !document.getElementById('web-read-selection')) {
      const read = element('a', 'Read selection ↓', 'web-selection-link');
      read.id = 'web-read-selection';
      read.href = '#edge-evidence';
      footer.append(read);
    }
    if (!selection && graph.root) renderNode(graph.root);
  }
  document.addEventListener('sg:ready', ready);
  document.addEventListener('sg:node-select', event => renderNode(event.detail?.nodeId));
  document.addEventListener('sg:edge-select', event => renderEdge(event.detail?.edgeId));
  window.SignalGraphEvidence = { renderNode, renderEdge };
  if (window.SignalGraphWeb) ready();
  if (!briefs.nodes) {
    fetch('/web-briefs.json', { credentials: 'same-origin' }).then(response => response.ok ? response.json() : null).then(data => {
      if (!data?.nodes) return;
      briefs = data;
      window.SignalGraphBriefs = data;
      if (selection?.kind === 'node') renderNode(selection.id);
      else if (selection?.kind === 'edge') renderEdge(selection.id);
    }).catch(() => {}); // Embedded graph records remain usable if the brief fetch fails.
  }
})();
