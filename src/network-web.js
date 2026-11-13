(() => {
  'use strict';
  const payload = document.getElementById('case-graph');
  const mount = document.getElementById('connection-tree');
  if (!payload || !mount) return;
  let graph;
  try { graph = JSON.parse(payload.textContent); } catch { return; }
  const nodes = new Map(graph.nodes.map(node => [node.id, node]));
  const edges = graph.edges.map((edge, index) => ({ ...edge, id: edge.id || `relationship-${index}`, source: edge.source || edge.from, target: edge.target || edge.to, type: edge.relationship_type || edge.type || 'relationship' })).filter(edge => nodes.has(edge.source) && nodes.has(edge.target));
  const edgesById = new Map(edges.map(edge => [edge.id, edge]));
  const SVG = 'http://www.w3.org/2000/svg';
  const categories = { ownership: 'Ownership', money: 'Money', family: 'Family', politics: 'Politics', other: 'Other' };
  const colors = { ownership: '#d6b87a', money: '#9fc79f', family: '#c6a7ce', politics: '#83c3d0', other: '#a6b3ac' };
  const enabled = new Set(Object.keys(categories));
  const ownership = new Set(['owns', 'ownership', 'ownership_interest', 'minority_ownership', 'equity_owner', 'reported_ownership', 'indirect_beneficial_owner', 'beneficiary_of', 'equity_investor', 'invests_in', 'disclosed_financial_interest', 'disclosed_household_interest', 'disclosed_spouse_interest', 'historical_security_holding', 'subsidiary', 'consolidated_subsidiaries', 'related_holding_structure', 'control', 'trustee']);
  const money = new Set(['royalties', 'token_proceeds', 'estimated_management_fees', 'reported_equity_purchase', 'capital_commitment', 'loan_commitment', 'direct_funding_award', 'disclosed_salary_source', 'disclosed_investment', 'bribery_benefit', 'alleged_payment', 'alleged_payment_route', 'federal_contract', 'government_obligation', 'program_financing', 'managed_care_capitation', 'healthcare_service_payments', 'reported_compensation', 'loan_obligation', 'agreement_award', 'contract_obligations', 'idiq_ceiling', 'backs']);
  const family = new Set(['family', 'parent_of', 'spouse', 'spouse_of', 'household_member']);
  const politics = new Set(['reported_advocacy', 'documented_advocacy', 'reported_policy_advocacy', 'potential_policy_benefit', 'public_office', 'former_public_office', 'presidential_pardon', 'official_intervention', 'former_chair_of', 'chair_of', 'member_of']);
  function category(edge) { return ownership.has(edge.type) ? 'ownership' : family.has(edge.type) ? 'family' : politics.has(edge.type) ? 'politics' : money.has(edge.type) || edge.is_money_flow ? 'money' : 'other'; }
  function nodeKind(node) {
    if (/household/i.test(node.label)) return 'Household';
    if (node.type === 'person_or_family') return /family|descendants/i.test(node.label) ? 'Family' : 'Person';
    if (/person|official/.test(node.type)) return 'Person';
    if (/government|agency|task_force|commission/.test(node.type)) return 'Public body';
    if (/trust/.test(node.type)) return 'Trust';
    if (node.type === 'family') return 'Family';
    return /company|business|entity|investment_firm/.test(node.type) ? 'Business' : node.type.replaceAll('_', ' ');
  }
  function html(tag, text, cls) { const item = document.createElement(tag); if (text) item.textContent = text; if (cls) item.className = cls; return item; }
  function svg(tag, attributes = {}) { const item = document.createElementNS(SVG, tag); for (const [key, value] of Object.entries(attributes)) item.setAttribute(key, String(value)); return item; }
  function button(text, label, action, cls = '') { const item = html('button', text, cls); item.type = 'button'; item.setAttribute('aria-label', label); item.addEventListener('click', action); return item; }
  function keyboardActivate(item, action) {
    item.addEventListener('keydown', event => { if (event.key === ' ' || event.key === 'Enter') event.preventDefault(); if (event.key === 'Enter' && !event.repeat) action(); });
    item.addEventListener('keyup', event => { if (event.key === ' ') { event.preventDefault(); action(); } });
  }
  function emit(type, detail) { document.dispatchEvent(new CustomEvent(type, { detail })); }
  const rootSelect = document.getElementById('tree-root');
  const requested = new URLSearchParams(location.search).get('node');
  let root = nodes.has(requested) ? requested : nodes.has(graph.root) ? graph.root : graph.nodes[0]?.id;
  if (!root) return;
  let scope = 2;
  let selectedNode = root;
  let selectedEdge = null;
  let hoveredNode = null;
  let hoveredEdge = null;
  let shownNodes = [];
  let shownEdges = [];
  let layout = new Map();
  let nodeElements = new Map();
  let edgeElements = new Map();
  let camera = { x: 0, y: 0, k: 1 };
  let width = 900;
  let height = 640;
  let clickSuppressedUntil = 0;
  let resizeFrame = 0;
  const status = document.getElementById('web-status') || html('p', '', 'web-status');
  if (!status.id) { status.id = 'web-status'; status.setAttribute('role', 'status'); status.setAttribute('aria-atomic', 'true'); }
  mount.replaceChildren();
  mount.classList.add('network-web');
  const toolbar = html('div', '', 'web-toolbar');
  const scopes = html('div', '', 'web-scope');
  scopes.setAttribute('role', 'group'); scopes.setAttribute('aria-label', 'Network reach');
  const scopeButtons = new Map();
  for (const [value, label] of [[2, 'Nearby'], [3, 'Wider'], [Infinity, 'All connected']]) {
    const item = button(label, `${label} relationships`, () => { scope = value; rebuild(); }, 'web-scope-button');
    item.setAttribute('aria-pressed', String(value === scope)); scopes.append(item); scopeButtons.set(value, item);
  }
  const filters = html('div', '', 'web-filters');
  filters.setAttribute('role', 'group'); filters.setAttribute('aria-label', 'Relationship types');
  const filterButtons = new Map();
  for (const [key, label] of Object.entries(categories)) {
    const item = button('', `${label} relationships`, () => { enabled.has(key) ? enabled.delete(key) : enabled.add(key); item.setAttribute('aria-pressed', String(enabled.has(key))); rebuild(); }, 'web-filter');
    item.dataset.category = key; item.setAttribute('aria-pressed', 'true');
    const swatch = html('span', '', 'web-swatch'); swatch.setAttribute('aria-hidden', 'true'); swatch.style.backgroundColor = colors[key];
    item.append(swatch, html('span', label)); filters.append(item); filterButtons.set(key, item);
  }
  const search = html('form', '', 'web-search'); search.action = location.pathname; search.method = 'get';
  const searchLabel = html('label', 'Find in this web'); searchLabel.htmlFor = 'web-name-search';
  const searchInput = html('input'); searchInput.id = 'web-name-search'; searchInput.name = 'q'; searchInput.type = 'search'; searchInput.placeholder = 'Name or company';
  searchInput.setAttribute('list', 'web-name-options'); searchInput.setAttribute('autocomplete', 'off'); searchInput.setAttribute('autocorrect', 'off'); searchInput.setAttribute('autocapitalize', 'none'); searchInput.setAttribute('spellcheck', 'false');
  const suggestions = html('datalist'); suggestions.id = 'web-name-options';
  [...nodes.values()].sort((a, b) => a.label.localeCompare(b.label)).forEach(node => { const option = html('option'); option.value = node.label; suggestions.append(option); });
  const searchButton = html('button', 'Find'); searchButton.type = 'submit';
  const searchResults = html('div', '', 'web-search-results'); searchResults.hidden = true;
  const normalize = text => text.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('en-US').replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
  search.addEventListener('submit', event => {
    event.preventDefault(); const query = normalize(searchInput.value); searchResults.replaceChildren(); searchResults.hidden = true;
    if (!query) { searchInput.focus(); return; }
    const exact = [...nodes.values()].filter(node => normalize(node.label) === query);
    const matches = exact.length ? exact : [...nodes.values()].filter(node => query.split(/\s+/).every(term => normalize(node.label).includes(term)));
    if (matches.length === 1) { searchInput.value = matches[0].label; focusNode(matches[0].id); return; }
    status.textContent = matches.length ? `${matches.length} matching entries. Choose a name below the search field.` : 'No matching entry in this web. Try a surname or company name.';
    if (matches.length) {
      for (const node of matches.slice(0, 12)) searchResults.append(button(node.label, `Focus connections for ${node.label}`, () => { searchInput.value = node.label; searchResults.hidden = true; focusNode(node.id); }, 'web-search-result'));
      searchResults.hidden = false;
    }
  });
  search.append(searchLabel, searchInput, searchButton, suggestions, searchResults);
  toolbar.append(search, scopes, filters);
  const viewport = html('div', '', 'web-viewport');
  const canvas = svg('svg', { class: 'web-svg', role: 'group', tabindex: '0', 'aria-label': 'Interactive relationship network', 'aria-describedby': 'web-help', width: '100%', height: '100%' });
  canvas.style.touchAction = 'none';
  const title = svg('title'); title.textContent = 'People, businesses and their documented relationships';
  const definitions = svg('defs');
  for (const key of Object.keys(categories)) {
    const marker = svg('marker', { id: `web-arrow-${key}`, viewBox: '0 0 10 10', refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: 'auto-start-reverse', markerUnits: 'userSpaceOnUse' });
    marker.append(svg('path', { d: 'M 1 1 L 9 5 L 1 9 Z', fill: colors[key] })); definitions.append(marker);
  }
  const scene = svg('g', { class: 'web-camera' });
  const edgeLayer = svg('g', { class: 'web-edges' });
  const nodeLayer = svg('g', { class: 'web-nodes' });
  scene.append(edgeLayer, nodeLayer); canvas.append(title, definitions, scene); viewport.append(canvas);
  const navigation = html('div', '', 'web-navigation');
  navigation.setAttribute('role', 'group'); navigation.setAttribute('aria-label', 'Map controls');
  navigation.append(button('+', 'Zoom in', () => zoomAt(camera.k * 1.25), 'web-zoom'), button('−', 'Zoom out', () => zoomAt(camera.k / 1.25), 'web-zoom'), button('Fit', 'Fit visible relationships', () => { fit(); announce(); }, 'web-fit'));
  for (const [glyph, label, dx, dy] of [['←', 'Pan left', 90, 0], ['↑', 'Pan up', 0, 90], ['↓', 'Pan down', 0, -90], ['→', 'Pan right', -90, 0]]) navigation.append(button(glyph, label, () => { camera.x += dx; camera.y += dy; applyCamera(); }, 'web-pan'));
  viewport.append(navigation);
  const footer = html('div', '', 'web-footer');
  const help = html('p', 'Select a name or line. Drag to rearrange; use the map controls to explore.', 'web-help'); help.id = 'web-help';
  const keyboard = html('details', '', 'web-keyboard'); keyboard.append(html('summary', 'Keyboard controls'), html('p', 'Tab to a name or connection, then press Enter or Space to inspect it. Alt + arrow keys move a focused name. On the map background, arrow keys pan and + or − zoom. Use Fit to restore the view.'));
  footer.append(help, keyboard); if (!status.isConnected) footer.append(status);
  mount.append(toolbar, viewport, footer);

  function announce(prefix = '') { status.textContent = `${prefix}${shownNodes.length} ${shownNodes.length === 1 ? 'entry' : 'entries'} · ${shownEdges.length} ${shownEdges.length === 1 ? 'connection' : 'connections'} · ${nodes.get(root).label}`; }
  function visibleGraph() {
    const eligible = edges.filter(edge => enabled.has(category(edge)));
    const adjacency = new Map([...nodes.keys()].map(id => [id, []]));
    eligible.forEach(edge => { adjacency.get(edge.source).push(edge.target); adjacency.get(edge.target).push(edge.source); });
    const distance = new Map([[root, 0]]); const queue = [root];
    for (let i = 0; i < queue.length; i++) {
      const id = queue[i]; if (distance.get(id) >= scope) continue;
      for (const neighbor of adjacency.get(id)) if (!distance.has(neighbor)) { distance.set(neighbor, distance.get(id) + 1); queue.push(neighbor); }
    }
    return { nodes: graph.nodes.filter(node => distance.has(node.id)), edges: eligible.filter(edge => distance.has(edge.source) && distance.has(edge.target)), distance };
  }
  function wrapLabel(label) {
    const words = label.split(/\s+/); const lines = []; let line = '';
    for (const word of words) { if (line && (line + ' ' + word).length > 22) { lines.push(line); line = word; } else line += (line ? ' ' : '') + word; }
    if (line) lines.push(line);
    return lines;
  }
  function hash(text) { let value = 2166136261; for (let i = 0; i < text.length; i++) value = Math.imul(value ^ text.charCodeAt(i), 16777619); return value >>> 0; }
  function calculateLayout(visible) {
    const count = visible.nodes.length;
    const positions = visible.nodes.map((node, i) => {
      const angle = (i * 2.399963229728653 + (hash(node.id) % 100) / 200);
      const radius = node.id === root ? 0 : 230 + visible.distance.get(node.id) * 100 + Math.sqrt(i) * 35;
      const lines = wrapLabel(node.label); const w = Math.max(158, Math.min(224, Math.max(...lines.map(s => s.length)) * 7.7 + 30));
      return { id: node.id, x: Math.cos(angle) * radius, y: Math.sin(angle) * radius, vx: 0, vy: 0, width: w, height: 34 + lines.length * 20, lines };
    });
    const lookup = new Map(positions.map(p => [p.id, p]));
    const iterations = count > 100 ? 180 : 230;
    for (let step = 0; step < iterations; step++) {
      const heat = 1 - step / iterations;
      for (let i = 0; i < count; i++) {
        const a = positions[i];
        for (let j = i + 1; j < count; j++) {
          const b = positions[j]; let dx = b.x - a.x; let dy = b.y - a.y;
          if (Math.abs(dx) + Math.abs(dy) < .01) { dx = 1; dy = .5; }
          const d2 = dx * dx + dy * dy; const length = Math.sqrt(d2);
          const push = Math.min(10, 6500 / Math.max(400, d2));
          a.vx -= dx / length * push; a.vy -= dy / length * push; b.vx += dx / length * push; b.vy += dy / length * push;
          const overlapX = (a.width + b.width) / 2 + 22 - Math.abs(dx);
          const overlapY = (a.height + b.height) / 2 + 22 - Math.abs(dy);
          if (overlapX > 0 && overlapY > 0) {
            if (overlapX < overlapY) { const force = Math.sign(dx) * overlapX * .16; a.vx -= force; b.vx += force; }
            else { const force = Math.sign(dy) * overlapY * .16; a.vy -= force; b.vy += force; }
          }
        }
      }
      for (const edge of visible.edges) {
        const a = lookup.get(edge.source); const b = lookup.get(edge.target); if (a === b) continue;
        const dx = b.x - a.x; const dy = b.y - a.y; const length = Math.max(1, Math.hypot(dx, dy));
        const target = (a.width + b.width) / 2 + 65;
        const spring = (length - target) * .018;
        a.vx += dx / length * spring; a.vy += dy / length * spring; b.vx -= dx / length * spring; b.vy -= dy / length * spring;
      }
      for (const point of positions) {
        if (point.id === root) { point.x = 0; point.y = 0; point.vx = 0; point.vy = 0; continue; }
        point.vx = (point.vx - point.x * .0007) * .72; point.vy = (point.vy - point.y * .0007) * .72;
        point.x += Math.max(-18, Math.min(18, point.vx)) * (.3 + heat);
        point.y += Math.max(-18, Math.min(18, point.vy)) * (.3 + heat);
      }
    }
    return lookup;
  }
  function screenPoint(event) { const rect = canvas.getBoundingClientRect(); return { x: (event.clientX - rect.left) * width / Math.max(1, rect.width), y: (event.clientY - rect.top) * height / Math.max(1, rect.height) }; }
  function world(point) { return { x: (point.x - camera.x) / camera.k, y: (point.y - camera.y) / camera.k }; }
  function applyCamera() { scene.setAttribute('transform', `translate(${camera.x} ${camera.y}) scale(${camera.k})`); }
  function zoomAt(value, center = { x: width / 2, y: height / 2 }, anchor = world(center)) { camera.k = Math.max(.12, Math.min(2.8, value)); camera.x = center.x - anchor.x * camera.k; camera.y = center.y - anchor.y * camera.k; applyCamera(); }
  function fit(readable = false) {
    const points = [...layout.values()]; if (!points.length) return;
    const left = Math.min(...points.map(p => p.x - p.width / 2)); const right = Math.max(...points.map(p => p.x + p.width / 2));
    const top = Math.min(...points.map(p => p.y - p.height / 2)); const bottom = Math.max(...points.map(p => p.y + p.height / 2));
    camera.k = Math.min(1.15, (width - 80) / Math.max(200, right - left), (height - 100) / Math.max(140, bottom - top));
    const useReadableFocus = readable && scope !== Infinity && camera.k < .78;
    if (useReadableFocus) camera.k = .78;
    camera.x = width / 2 - (useReadableFocus ? 0 : (left + right) / 2) * camera.k; camera.y = height / 2 - (useReadableFocus ? 0 : (top + bottom) / 2) * camera.k; applyCamera();
  }
  function ensureVisible(nodeId) {
    const point = layout.get(nodeId); if (!point) return;
    const x = point.x * camera.k + camera.x; const y = point.y * camera.k + camera.y;
    if (x - point.width * camera.k / 2 < 12 || x + point.width * camera.k / 2 > width - 12 || y - point.height * camera.k / 2 < 12 || y + point.height * camera.k / 2 > height - 12) {
      camera.x = width / 2 - point.x * camera.k; camera.y = height / 2 - point.y * camera.k; applyCamera();
    }
  }
  function edgePath(edge) {
    const a = layout.get(edge.source); const b = layout.get(edge.target);
    if (a.id === b.id) return `M ${a.x + a.width / 3} ${a.y - a.height / 2} C ${a.x + a.width} ${a.y - 110}, ${a.x - a.width} ${a.y - 110}, ${a.x - a.width / 3} ${a.y - a.height / 2}`;
    const dx = b.x - a.x; const dy = b.y - a.y;
    const factorA = 1 / Math.max(Math.abs(dx) / (a.width / 2 + 7), Math.abs(dy) / (a.height / 2 + 7), .001);
    const factorB = 1 / Math.max(Math.abs(dx) / (b.width / 2 + 9), Math.abs(dy) / (b.height / 2 + 9), .001);
    const start = { x: a.x + dx * factorA, y: a.y + dy * factorA }; const end = { x: b.x - dx * factorB, y: b.y - dy * factorB };
    const parallel = shownEdges.filter(e => (e.source === edge.source && e.target === edge.target) || (e.source === edge.target && e.target === edge.source));
    const order = parallel.findIndex(e => e.id === edge.id); const curve = (order - (parallel.length - 1) / 2) * 30;
    const length = Math.max(1, Math.hypot(dx, dy));
    return `M ${start.x} ${start.y} Q ${(start.x + end.x) / 2 - dy / length * curve} ${(start.y + end.y) / 2 + dx / length * curve} ${end.x} ${end.y}`;
  }
  function drawPositions() {
    for (const [id, item] of nodeElements) { const p = layout.get(id); item.setAttribute('transform', `translate(${p.x} ${p.y})`); }
    for (const edge of shownEdges) { const item = edgeElements.get(edge.id); for (const shape of item.querySelectorAll('path')) shape.setAttribute('d', edgePath(edge)); }
  }
  function highlight() {
    const edgeId = hoveredEdge || (!hoveredNode ? selectedEdge : null); const nodeId = hoveredNode || (!edgeId ? selectedNode : null);
    const active = new Set(); const activeEdges = new Set();
    if (edgeId) { const edge = edgesById.get(edgeId); if (edge) { active.add(edge.source); active.add(edge.target); activeEdges.add(edgeId); } }
    else if (nodeId) { active.add(nodeId); for (const edge of shownEdges) if (edge.source === nodeId || edge.target === nodeId) { active.add(edge.source); active.add(edge.target); activeEdges.add(edge.id); } }
    for (const [id, item] of nodeElements) { item.classList.toggle('is-selected', id === selectedNode); item.classList.toggle('is-neighbor', active.has(id)); item.classList.toggle('is-dimmed', active.size > 0 && !active.has(id)); item.setAttribute('aria-pressed', String(id === selectedNode)); }
    for (const [id, item] of edgeElements) { item.classList.toggle('is-selected', id === selectedEdge); item.classList.toggle('is-neighbor', activeEdges.has(id)); item.classList.toggle('is-dimmed', active.size > 0 && !activeEdges.has(id)); item.setAttribute('aria-pressed', String(id === selectedEdge)); }
  }
  function selectNode(nodeId) { if (!nodes.has(nodeId)) return; selectedNode = nodeId; selectedEdge = null; highlight(); emit('sg:node-select', { nodeId }); announce(`${nodes.get(nodeId).label} selected. `); }
  function selectEdge(edgeId) { if (!edgesById.has(edgeId)) return; selectedEdge = edgeId; selectedNode = null; highlight(); emit('sg:edge-select', { edgeId }); announce('Connection selected. '); }
  function focusNode(nodeId) {
    if (!nodes.has(nodeId)) return;
    root = nodeId; selectedNode = nodeId; selectedEdge = null; if (rootSelect) rootSelect.value = nodeId;
    const url = new URL(location.href); url.searchParams.set('node', nodeId); history.replaceState(null, '', url);
    rebuild(); selectNode(nodeId);
  }
  function rebuild() {
    hoveredNode = null; hoveredEdge = null;
    const visible = visibleGraph(); shownNodes = visible.nodes; shownEdges = visible.edges; layout = calculateLayout(visible);
    nodeElements = new Map(); edgeElements = new Map(); edgeLayer.replaceChildren(); nodeLayer.replaceChildren();
    for (const edge of shownEdges) {
      const key = category(edge); const item = svg('g', { class: 'web-edge', 'data-edge-id': edge.id, 'data-category': key, role: 'button', tabindex: 0, 'aria-label': `${nodes.get(edge.source).label} to ${nodes.get(edge.target).label}: ${edge.label || edge.type.replaceAll('_', ' ')}`, 'aria-pressed': 'false' });
      const line = svg('path', { class: 'web-edge-line', fill: 'none', stroke: colors[key], 'stroke-width': 1.6, 'marker-end': `url(#web-arrow-${key})`, 'vector-effect': 'non-scaling-stroke' });
      const hit = svg('path', { class: 'web-edge-hit', fill: 'none', stroke: 'transparent', 'stroke-width': 18, 'vector-effect': 'non-scaling-stroke' });
      const label = svg('title'); label.textContent = `${categories[key]} · ${edge.label || edge.type.replaceAll('_', ' ')}`; item.append(line, hit, label);
      item.addEventListener('click', () => { if (performance.now() > clickSuppressedUntil) selectEdge(edge.id); });
      keyboardActivate(item, () => selectEdge(edge.id));
      item.addEventListener('pointerenter', () => { hoveredEdge = edge.id; highlight(); }); item.addEventListener('pointerleave', () => { hoveredEdge = null; highlight(); });
      item.addEventListener('focus', () => { hoveredEdge = edge.id; highlight(); }); item.addEventListener('blur', () => { hoveredEdge = null; highlight(); });
      edgeLayer.append(item); edgeElements.set(edge.id, item);
    }
    for (const node of shownNodes) {
      const point = layout.get(node.id); const kind = nodeKind(node);
      const item = svg('g', { class: `web-node${node.id === root ? ' is-root' : ''}`, 'data-node-id': node.id, 'data-kind': kind.toLowerCase().replaceAll(' ', '-'), role: 'button', tabindex: 0, 'aria-label': `${node.label}, ${kind}. Select to inspect; Alt and arrow keys move.`, 'aria-pressed': 'false' });
      const attrs = { x: -point.width / 2, y: -point.height / 2, width: point.width, height: point.height, rx: 20 };
      item.append(svg('rect', { ...attrs, class: 'web-node-halo', x: attrs.x - 5, y: attrs.y - 5, width: attrs.width + 10, height: attrs.height + 10, rx: 25 }), svg('rect', { ...attrs, class: 'web-node-body' }));
      item.append(svg('circle', { class: 'web-node-dot', cx: -point.width / 2 + 14, cy: point.height / 2 - 15, r: 3 }));
      const text = svg('text', { class: 'web-node-label', x: 0, y: -point.height / 2 + 23, 'text-anchor': 'middle' });
      point.lines.forEach((line, i) => { const span = svg('tspan', { x: 0, dy: i ? 20 : 0 }); span.textContent = line; text.append(span); });
      const sub = svg('text', { class: 'web-node-type', x: -point.width / 2 + 23, y: point.height / 2 - 11 }); sub.textContent = node.id === root ? `${kind} · Focus` : kind;
      item.append(text, sub); item.style.touchAction = 'none';
      item.addEventListener('click', () => { if (performance.now() > clickSuppressedUntil) selectNode(node.id); });
      keyboardActivate(item, () => selectNode(node.id));
      item.addEventListener('keydown', event => {
        if (event.altKey && ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) {
          event.preventDefault(); const point = layout.get(node.id); point.x += event.key === 'ArrowRight' ? 24 : event.key === 'ArrowLeft' ? -24 : 0; point.y += event.key === 'ArrowDown' ? 24 : event.key === 'ArrowUp' ? -24 : 0; drawPositions(); announce(`${node.label} repositioned. `);
        }
      });
      item.addEventListener('pointerenter', () => { hoveredNode = node.id; highlight(); }); item.addEventListener('pointerleave', () => { hoveredNode = null; highlight(); });
      item.addEventListener('focus', () => { ensureVisible(node.id); hoveredNode = node.id; highlight(); }); item.addEventListener('blur', () => { hoveredNode = null; highlight(); });
      nodeLayer.append(item); nodeElements.set(node.id, item);
    }
    for (const [value, item] of scopeButtons) item.setAttribute('aria-pressed', String(scope === value));
    drawPositions(); fit(true); highlight(); announce();
  }

  const pointers = new Map(); let gesture = null; let pinch = null;
  canvas.addEventListener('pointerdown', event => {
    if (event.button !== 0) return;
    const point = screenPoint(event); pointers.set(event.pointerId, point); canvas.setPointerCapture(event.pointerId);
    if (pointers.size === 2) {
      const [a, b] = [...pointers.values()]; const center = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
      pinch = { distance: Math.max(1, Math.hypot(a.x - b.x, a.y - b.y)), scale: camera.k, anchor: world(center) }; gesture = null; return;
    }
    const nodeElement = event.target.closest('[data-node-id]'); const nodeId = nodeElement?.getAttribute('data-node-id');
    const edgeId = event.target.closest('[data-edge-id]')?.getAttribute('data-edge-id');
    const start = nodeId ? layout.get(nodeId) : camera;
    gesture = { pointer: event.pointerId, nodeId, edgeId, startPoint: point, x: start.x, y: start.y, moved: false };
  });
  canvas.addEventListener('pointermove', event => {
    if (!pointers.has(event.pointerId)) return;
    const point = screenPoint(event); pointers.set(event.pointerId, point);
    if (pinch && pointers.size >= 2) {
      const [a, b] = [...pointers.values()]; zoomAt(pinch.scale * Math.hypot(a.x - b.x, a.y - b.y) / pinch.distance, { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }, pinch.anchor); clickSuppressedUntil = performance.now() + 350; return;
    }
    if (!gesture || gesture.pointer !== event.pointerId) return;
    const dx = point.x - gesture.startPoint.x; const dy = point.y - gesture.startPoint.y;
    if (!gesture.moved && Math.hypot(dx, dy) < 4) return;
    gesture.moved = true; viewport.classList.add('is-dragging');
    if (gesture.nodeId) { const p = layout.get(gesture.nodeId); p.x = gesture.x + dx / camera.k; p.y = gesture.y + dy / camera.k; drawPositions(); }
    else { camera.x = gesture.x + dx; camera.y = gesture.y + dy; applyCamera(); }
  });
  function finishPointer(event) {
    if (gesture?.moved) { clickSuppressedUntil = performance.now() + 350; if (gesture.nodeId) announce(`${nodes.get(gesture.nodeId).label} repositioned. `); }
    else if (event.type === 'pointerup' && gesture && pointers.size === 1) {
      if (gesture.nodeId) selectNode(gesture.nodeId); else if (gesture.edgeId) selectEdge(gesture.edgeId);
      clickSuppressedUntil = performance.now() + 350;
    }
    pointers.delete(event.pointerId); gesture = null; pinch = null; viewport.classList.remove('is-dragging');
  }
  canvas.addEventListener('pointerup', finishPointer); canvas.addEventListener('pointercancel', finishPointer); canvas.addEventListener('lostpointercapture', finishPointer);
  canvas.addEventListener('wheel', event => { event.preventDefault(); const delta = event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? height : 1); zoomAt(camera.k * Math.exp(-Math.max(-120, Math.min(120, delta)) * .0025), screenPoint(event)); }, { passive: false });
  canvas.addEventListener('keydown', event => {
    if (event.target !== canvas || event.altKey || event.ctrlKey || event.metaKey) return;
    if (event.key === '+' || event.key === '=') { event.preventDefault(); zoomAt(camera.k * 1.2); }
    else if (event.key === '-') { event.preventDefault(); zoomAt(camera.k / 1.2); }
    else if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) { event.preventDefault(); camera.x += event.key === 'ArrowRight' ? -70 : event.key === 'ArrowLeft' ? 70 : 0; camera.y += event.key === 'ArrowDown' ? -70 : event.key === 'ArrowUp' ? 70 : 0; applyCamera(); }
  });
  function resize() { const rect = canvas.getBoundingClientRect(); width = Math.max(280, rect.width || 900); height = Math.max(420, rect.height || 640); canvas.setAttribute('viewBox', `0 0 ${width} ${height}`); fit(true); }
  if ('ResizeObserver' in window) new ResizeObserver(() => { cancelAnimationFrame(resizeFrame); resizeFrame = requestAnimationFrame(resize); }).observe(viewport);
  else window.addEventListener('resize', resize, { passive: true });
  rootSelect?.addEventListener('change', () => focusNode(rootSelect.value));
  document.addEventListener('sg:focus', event => focusNode(event.detail?.nodeId));
  window.addEventListener('popstate', () => { const id = new URLSearchParams(location.search).get('node'); if (nodes.has(id)) { root = id; if (rootSelect) rootSelect.value = id; selectedNode = id; selectedEdge = null; rebuild(); selectNode(id); } });
  if (rootSelect) rootSelect.value = root;
  document.querySelector('.tree-explorer')?.removeAttribute('hidden');
  const fallback = document.querySelector('.relationship-list'); if (fallback) fallback.open = false;
  resize(); rebuild();
  window.SignalGraphWeb = { graph: { ...graph, edges }, nodes, focusNode, selectNode, selectEdge, getVisibleGraph: () => ({ nodes: shownNodes, edges: shownEdges, root, scope, enabledCategories: [...enabled] }) };
  const ready = () => { emit('sg:ready', { graph: window.SignalGraphWeb.graph, nodes }); selectNode(root); };
  if (document.readyState === 'complete') setTimeout(ready, 0); else document.addEventListener('DOMContentLoaded', ready, { once: true });
})();
