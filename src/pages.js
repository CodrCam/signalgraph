const progress = document.querySelector('.reading-line');
function updateProgress() {
  if (!progress) return;
  const range = document.documentElement.scrollHeight - innerHeight;
  progress.style.transform = `scaleX(${range > 0 ? Math.min(1, scrollY / range) : 0})`;
}
addEventListener('scroll', updateProgress, {passive:true});
addEventListener('resize', updateProgress);
updateProgress();
function normalizeSearch(value) {
  return value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('en-US').replace(/['’]/g, '').replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
}
function matchesSearch(text, query) {
  const terms = normalizeSearch(query).split(/\s+/).filter(Boolean);
  return terms.every(term => normalizeSearch(text).includes(term));
}
const siteSearch = document.querySelector('[data-site-search]');
if (siteSearch) siteSearch.hidden = false;
const globalSearch = document.getElementById('site-name-search');
const filters = document.querySelector('[data-people-filters]');
if (filters) {
  filters.hidden = false;
  const search = document.getElementById('person-search');
  const categories = [...filters.querySelectorAll('input[name="category"]')];
  const company = document.getElementById('person-company');
  const cards = [...document.querySelectorAll('[data-person]')];
  const count = document.getElementById('results-count');
  const empty = document.getElementById('no-results');
  const clear = document.querySelector('[data-person-clear]');
  let announce;
  const selectedCategory = () => categories.find(input => input.checked)?.value || 'all';
  function filterPeople(updateURL = true, pushHistory = false) {
    const query = search.value.trim();
    const category = selectedCategory();
    const matchesByCategory = {all: 0, documented: 0, unquantified: 0};
    let visible = 0;
    for (const card of cards) {
      const matchesBase = matchesSearch(card.dataset.search, query) && (company.value === 'all' || card.dataset.companyName === company.value);
      if (matchesBase) {
        matchesByCategory.all++;
        matchesByCategory[card.dataset.category]++;
      }
      const matches = matchesBase && (category === 'all' || card.dataset.category === category);
      card.hidden = !matches;
      if (matches) visible++;
    }
    categories.forEach(input => {
      input.nextElementSibling.querySelector('span').textContent = matchesByCategory[input.value];
    });
    empty.hidden = visible > 0;
    clear.hidden = !query && category === 'all' && company.value === 'all';
    if (globalSearch) globalSearch.value = search.value;
    if (updateURL) {
      const url = new URL(location.href);
      if (query) url.searchParams.set('q', query); else url.searchParams.delete('q');
      if (category !== 'all') url.searchParams.set('category', category); else url.searchParams.delete('category');
      if (company.value !== 'all') url.searchParams.set('company', company.value); else url.searchParams.delete('company');
      if (url.href !== location.href) history[pushHistory ? 'pushState' : 'replaceState'](null, '', url);
    }
    clearTimeout(announce);
    announce = setTimeout(() => { count.textContent = `${visible} ${visible === 1 ? 'profile' : 'profiles'}${query ? ` matching “${query}”` : ''}`; }, 180);
  }
  function loadQuery() {
    const params = new URLSearchParams(location.search);
    search.value = params.get('q') || '';
    const requested = params.get('category');
    const category = ['documented', 'unquantified'].includes(requested) ? requested : 'all';
    categories.forEach(input => { input.checked = input.value === category; });
    const requestedCompany = params.get('company');
    company.value = [...company.options].some(option => option.value === requestedCompany) ? requestedCompany : 'all';
    filterPeople(false);
  }
  search.addEventListener('input', () => filterPeople());
  categories.forEach(input => input.addEventListener('change', () => filterPeople(true, true)));
  company.addEventListener('change', () => filterPeople(true, true));
  filters.addEventListener('submit', event => { event.preventDefault(); filterPeople(); });
  function resetFilters() {
    search.value = ''; company.value = 'all';
    categories.forEach(input => { input.checked = input.value === 'all'; });
    filterPeople(true, true); search.focus();
  }
  clear.addEventListener('click', resetFilters);
  document.querySelectorAll('[data-person-reset]').forEach(button => button.addEventListener('click', resetFilters));
  if (siteSearch && siteSearch.querySelector('form').getAttribute('action').includes('individual-benefits.html')) siteSearch.querySelector('form').addEventListener('submit', event => {
    event.preventDefault(); search.value = globalSearch.value; company.value = 'all';
    categories.forEach(input => { input.checked = input.value === 'all'; });
    filterPeople();
    document.getElementById('directory').scrollIntoView(); search.focus({preventScroll:true});
  });
  addEventListener('popstate', loadQuery);
  loadQuery();
}
const companyFilters = document.querySelector('[data-company-filters]');
if (companyFilters) {
  companyFilters.hidden = false;
  const input = document.getElementById('company-search');
  const entries = [...document.querySelectorAll('[data-company]')];
  const count = document.getElementById('company-count');
  const clear = document.querySelector('[data-company-clear]');
  let announce;
  function filterCompanies() {
    let visible = 0;
    for (const entry of entries) {
      entry.hidden = !matchesSearch(entry.dataset.search, input.value);
      if (!entry.hidden) visible++;
    }
    clear.hidden = !input.value;
    document.getElementById('company-empty').hidden = visible > 0;
    clearTimeout(announce);
    announce = setTimeout(() => { count.textContent = `${visible} of ${entries.length} companies`; }, 180);
  }
  input.addEventListener('input', filterCompanies);
  companyFilters.addEventListener('submit', event => {event.preventDefault(); filterCompanies();});
  clear.addEventListener('click', () => {input.value = ''; filterCompanies(); input.focus();});
}
document.querySelectorAll('[data-print]').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('details').forEach(detail => {detail.open = true;});
  window.print();
}));
addEventListener('beforeprint', () => document.querySelectorAll('details').forEach(detail => {detail.open = true;}));
