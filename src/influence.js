(() => {
  'use strict';
  const norm = value => String(value).normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('en-US').replace(/['’]/g, '').replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
  const matches = (text, query) => norm(query).split(/\s+/).filter(Boolean).every(term => norm(text).includes(term));
  const form = document.querySelector('[data-influence-filter]');
  if (form) {
    form.hidden = false;
    const input = document.getElementById('influence-search');
    const party = document.getElementById('influence-party');
    const cards = [...document.querySelectorAll('[data-case]')];
    let announce;
    const filter = (save = true) => {
      let count = 0;
      cards.forEach(card => { card.hidden = !matches(card.dataset.search, input.value) || (party.value !== 'all' && card.dataset.party !== party.value); if (!card.hidden) count++; });
      document.getElementById('influence-empty').hidden = count > 0;
      clearTimeout(announce); announce = setTimeout(() => { document.getElementById('influence-count').textContent = `${count} ${count === 1 ? 'investigation' : 'investigations'}`; }, 180);
      if (save) { const url = new URL(location.href); input.value.trim() ? url.searchParams.set('q', input.value.trim()) : url.searchParams.delete('q'); party.value !== 'all' ? url.searchParams.set('party', party.value) : url.searchParams.delete('party'); history.replaceState(null, '', url); }
    };
    const load = () => { const p = new URLSearchParams(location.search); input.value = p.get('q') || ''; party.value = [...party.options].some(o => o.value === p.get('party')) ? p.get('party') : 'all'; filter(false); };
    input.addEventListener('input', () => filter()); party.addEventListener('change', () => filter());
    form.addEventListener('submit', e => { e.preventDefault(); filter(); });
    form.addEventListener('reset', () => setTimeout(() => { filter(); input.focus(); }, 0));
    addEventListener('popstate', load); load();
  }
  const allSearch = document.getElementById('all-search');
  if (allSearch) {
    const rows = [...document.querySelectorAll('[data-search-result]')];
    let announce;
    const filter = (save = true) => {
      let count = 0; rows.forEach(row => { row.hidden = !matches(row.dataset.search, allSearch.value); if (!row.hidden) count++; });
      document.getElementById('search-empty').hidden = count > 0;
      clearTimeout(announce); announce = setTimeout(() => { document.getElementById('search-count').textContent = `${count} ${count === 1 ? 'result' : 'results'}${allSearch.value.trim() ? ` for “${allSearch.value.trim()}”` : ''}`; }, 180);
      if (save) { const url = new URL(location.href); allSearch.value.trim() ? url.searchParams.set('q', allSearch.value.trim()) : url.searchParams.delete('q'); history.replaceState(null, '', url); }
    };
    const load = () => { allSearch.value = new URLSearchParams(location.search).get('q') || ''; filter(false); };
    allSearch.addEventListener('input', () => filter()); allSearch.form.addEventListener('submit', e => { e.preventDefault(); filter(); }); addEventListener('popstate', load); load();
  }
  const graphScript = document.getElementById('case-graph');
  if (!graphScript) return;
  const graph = JSON.parse(graphScript.textContent);
  const nodes = new Map(graph.nodes.map(n => [n.id, n]));
  const rootSelect = document.getElementById('tree-root');
  const tree = document.getElementById('connection-tree');
  const evidence = document.getElementById('edge-evidence');
  const element = (tag, text, cls) => { const e = document.createElement(tag); if (text) e.textContent = text; if (cls) e.className = cls; return e; };
  const statusLabel = status => ({
    relationship_and_company_compensation_supported_personal_government_receipts_unquantified: 'Disclosed compensation and business role',
    relationship_supported_personal_government_receipts_unquantified: 'Documented relationship',
    documented_relationship: 'Documented relationship', documented_by_OCE: 'Documented by ethics investigators',
    adjudicated_scheme: 'Established at trial', trial_record: 'Trial record', alleged: 'Alleged',
    described_in_indictment: 'Alleged in indictment', attributed_estimate: 'Attributed estimate',
    disclosed: 'Disclosed', documented: 'Documented', reported: 'Reported'
  }[status] || 'See cited evidence');
  const relationshipLabel = type => ({
    documented_executive_connection: 'Executive role', documented_director_connection: 'Board role',
    documented_leadership_or_ownership_connection: 'Leadership or ownership', disclosed_investment: 'Investment income',
    disclosed_salary_source: 'Salary source', bribery_benefit: 'Bribery', beneficiary_of: 'Trust beneficiary',
    business_operator: 'Business role', parent_of: 'Family', spouse_of: 'Spouse', signatory_for: 'Deal signatory',
    related_holding_structure: 'Holding company', backs: 'Financial backing'
  }[type] || type.replaceAll('_', ' '));
  const nodeLabel = node => ({
    person_or_family: /family|descendants/i.test(node.label) ? 'Family' : 'Person', family: 'Family member',
    entity_group: 'Related entities', business_group: 'Business group', agency_group: 'Federal buyers',
    ownership_group: 'Ownership interests', investor_group: 'Investors', fund_group: 'Investment funds',
    counterparty: 'Business counterparty', sovereign_investor: 'State investor'
  }[node.type] || node.type.replaceAll('_', ' '));
  function showEdge(edge, button, reveal = false) {
    document.querySelectorAll('.tree-relation').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    evidence.replaceChildren(element('p', relationshipLabel(edge.type), 'edge-kind'), element('h3', `${nodes.get(edge.source).label} → ${nodes.get(edge.target).label}`), element('p', edge.label), element('p', String(edge.period), 'case-period'));
    evidence.append(element('p', statusLabel(edge.status)));
    if (edge.aggregation) evidence.append(element('p', edge.aggregation));
    if (edge.qualification) evidence.append(element('p', edge.qualification));
    if (edge.type === 'disclosed_investment' && !edge.qualification) evidence.append(element('p', 'Disclosed investment income; the full gain is not a direct payment by the issuer.'));
    for (const id of edge.source_ids || []) {
      const source = graph.sources[id]; if (!source) continue;
      const a = element('a', source.title + ' ↗'); a.href = source.url; a.target = '_blank'; a.rel = 'noopener noreferrer'; evidence.append(a);
      if (source.locator) evidence.append(element('p', source.locator, 'small-note'));
    }
    if (reveal && matchMedia('(max-width: 1000px)').matches) {
      const back = element('button', 'Back to connection ↑', 'clear-search'); back.type = 'button'; back.addEventListener('click', () => { button.scrollIntoView({block:'center'}); button.focus({preventScroll:true}); }); evidence.append(back);
      evidence.scrollIntoView({block:'start'}); const heading = evidence.querySelector('h3'); heading.tabIndex = -1; heading.focus({preventScroll:true});
    }
  }
  function render(root) {
    const depth = new Map([[root, 0]]); const parentEdge = new Map(); const queue = [root];
    while (queue.length) {
      const id = queue.shift();
      if (graph.max_depth && depth.get(id) >= graph.max_depth) continue;
      for (const edge of graph.edges) {
        const other = edge.source === id ? edge.target : edge.target === id ? edge.source : null;
        if (other && !depth.has(other)) { depth.set(other, depth.get(id) + 1); parentEdge.set(other, edge); queue.push(other); }
      }
    }
    const max = Math.max(...depth.values()); const layers = element('div', '', 'tree-layers'); const renderedEdges = new Set();
    for (let level = 0; level <= max + (graph.connected_only ? 0 : 1); level++) {
      const items = graph.nodes.filter(n => level <= max ? depth.get(n.id) === level : !depth.has(n.id));
      if (!items.length) continue;
      const layer = element('div', '', 'tree-layer'); layer.append(element('h3', level === 0 ? 'Starting point' : level > max ? 'Other documented connections' : `Layer ${level}`));
      for (const node of items) {
        const branch = element('div', '', 'tree-branch');
        const b = element('button', node.label, 'tree-node' + (node.id === root ? ' root' : '')); b.type = 'button'; b.setAttribute('aria-label', `Start the connection tree with ${node.label}`); b.append(element('small', nodeLabel(node)));
        b.addEventListener('click', () => { rootSelect.value = node.id; render(node.id); rootSelect.focus({preventScroll: true}); }); branch.append(b);
        const linked = graph.edges.filter(e => e.source === node.id || e.target === node.id);
        const chosen = parentEdge.get(node.id);
        const edges = linked.filter(e => !renderedEdges.has(e.id) && (depth.get(e.source === node.id ? e.target : e.source) <= level || !depth.has(e.source === node.id ? e.target : e.source)));
        if (chosen) edges.sort((a, b) => a.id === chosen.id ? -1 : b.id === chosen.id ? 1 : 0);
        for (const edge of edges) {
          renderedEdges.add(edge.id);
          const other = edge.source === node.id ? edge.target : edge.source;
          const rb = element('button', '', 'tree-relation'); rb.append(element('span', `${nodes.get(edge.source).label} → ${nodes.get(edge.target).label}`, 'relation-direction'), element('span', edge.label)); rb.type = 'button'; rb.setAttribute('aria-pressed', 'false'); rb.addEventListener('click', event => showEdge(edge, rb, event.isTrusted)); branch.append(rb);
        }
        layer.append(branch);
      }
      layers.append(layer);
    }
    tree.replaceChildren(layers);
    if (graph.connected_only) {
      const url = new URL(location.href); url.searchParams.set('node', root); history.replaceState(null, '', url);
    }
    const first = tree.querySelector('.tree-relation');
    if (first) first.click();
    else {
      evidence.replaceChildren(element('h3', nodes.get(root).label), element('p', 'No linked relationship is recorded for this entry in the current network.'));
      for (const id of nodes.get(root).source_ids || []) {const s=graph.sources[id]; if(s){const a=element('a',s.title+' ↗');a.href=s.url;a.target='_blank';a.rel='noopener noreferrer';evidence.append(a);}}
    }
  }
  document.querySelector('.tree-control').hidden = false;
  document.querySelector('.tree-explorer').hidden = false;
  document.querySelector('.relationship-list').open = false;
  rootSelect.addEventListener('change', () => render(rootSelect.value));
  const requestedRoot = new URLSearchParams(location.search).get('node');
  rootSelect.value = requestedRoot && nodes.has(requestedRoot) ? requestedRoot : graph.root;
  render(rootSelect.value);
})();
