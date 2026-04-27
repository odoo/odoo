/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('account_reports_search', {
    url: '/odoo/action-account_reports.action_account_report_general_ledger',
    steps: () => [
        {
            content: "click search",
            trigger: '.o_searchview_input',
            run: 'click',
        },
        {
            content: 'insert text in the searchbar',
            trigger: '.o_searchview_input',
            run: "edit 40",
        },
        {
            content: 'test if the product sale line is present',
            trigger: '.line_name:contains("400000 Product Sales")',
            run: "click",
        },
        {
            content: "click search",
            trigger: '.o_searchview_input',
            run: 'click',
        },
        {
            content: 'insert text in the search bar',
            trigger: '.o_searchview_input',
            run: "edit Account",
        },
        {
            content: 'test if the receivable line is present',
            trigger: '.line_name:contains("121000 Account Receivable")',
            run: 'click',
        },
        {
            content: 'check that the product sale line is not present',
            trigger: '.line_name:not(:contains("400000 Product Sales"))',
        },
    ]
});
