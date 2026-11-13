"""People-first directory markup for the static site."""
from html import escape


def render_directory(people, person_card, threshold):
    disclosed = sum(bool(person['qualifies']) for person in people)
    unpriced = len(people) - disclosed
    companies = sorted({person['company'] for person in people}, key=str.casefold)
    options = ''.join(f'<option value="{escape(name, quote=True)}">{escape(name)}</option>' for name in companies)
    choices = [('all', 'All', len(people)), ('documented', 'Disclosed', disclosed), ('unquantified', 'Unpriced', unpriced)]
    categories = ''.join(
        f'<div class="directory-choice"><input type="radio" id="category-{value}" name="category" value="{value}"'
        + (' checked' if value == 'all' else '')
        + f'><label for="category-{value}">{label} <span>{count}</span></label></div>'
        for value, label, count in choices
    )
    cards = ''.join(person_card(person) for person in sorted(people, key=lambda person: person['name'].casefold()))
    return f'''<section class="content-section wrap directory-section" id="directory">
<div class="directory-heading"><h2>Directory</h2><nav class="directory-links" aria-label="Beneficiary details"><a href="#comparisons">Disclosures</a><a href="#stock-sales">Share Sales</a><a href="methods.html#inclusion">Method</a></nav></div>
<search aria-label="Beneficiaries"><form class="directory-controls" data-people-filters hidden action="individual-benefits.html#directory" method="get" aria-label="Filter beneficiaries">
<div class="directory-search"><label for="person-search">Name or company</label><div class="filter-search"><input id="person-search" name="q" type="search" placeholder="Search people, companies or roles" autocomplete="off" autocapitalize="none" autocorrect="off" spellcheck="false" enterkeyhint="search"><button class="clear-search" data-person-clear type="button" hidden>Reset</button></div></div>
<div class="directory-company"><label for="person-company">Company</label><select id="person-company" name="company"><option value="all">All companies</option>{options}</select></div>
<fieldset class="directory-categories"><legend>Show</legend>{categories}</fieldset>
</form></search>
<noscript><p class="small-note">All profiles are listed below. Use your browser’s Find command to search names.</p></noscript>
<div class="directory-context"><p class="results-count" id="results-count" role="status" aria-atomic="true">{len(people)} profiles</p><details class="directory-key"><summary>Reading the amounts</summary><p>Disclosed: at least one sourced financial measure of ${threshold:,.0f} or more in the period shown. Unpriced: a documented ownership or leadership connection without a qualifying personal amount. Compensation, equity and sales are different measures; company payments are not personal proceeds.</p></details></div>
<div class="people-grid" id="people-results">{cards}</div>
<div id="no-results" class="no-results" hidden><h3>No matches</h3><p>Try a surname, change the company, or reset the filters.</p><button class="clear-search" data-person-reset type="button">Reset filters</button></div>
</section>'''
