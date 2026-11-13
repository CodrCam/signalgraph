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
})();
