/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Makes sure that blog search can be used with the date filtering.
 */
registry.category("web_tour.tours").add("blog_autocomplete_with_date", {
    url: '/blog',
    steps: () => [{
    content: "Select first month",
    trigger: 'select[name=archive]',
    run: "selectByIndex 1",
    expectUnloadPage: true,
},
{
    trigger: '#o_wblog_posts_loop span:has(i.fa-calendar-o):has(a[href="/blog"])',
},
{
    content: "Enter search term",
    trigger: '.o_searchbar_form input',
    run: "edit a",
},
{
    trigger: ".o_searchbar_form .o_dropdown_menu .o_search_result_item",
},
{
    content: "Wait for suggestions then click on search icon",
    trigger: '.o_searchbar_form button:has(i.oi-search)',
    run: "click",
    expectUnloadPage: true,
}, {
    content: "Ensure both filters are applied",
    trigger: `#o_wblog_posts_loop:has(span a[href="/blog?search=a"]):has(span i.fa-calendar-o):has(span a[href^="/blog?date_begin"]):has(span i.fa-search)`,
}]});
