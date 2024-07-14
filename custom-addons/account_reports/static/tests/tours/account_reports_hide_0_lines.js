/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('account_reports_hide_0_lines', {
    test: true,
    url: '/web?#action=account_reports.action_account_report_bs',
    steps: () => [
        {
            content: 'test if the Bank and Cash line is present (but the value is 0)',
            trigger: '.line_name:contains("Bank and Cash Accounts")',
        },
        {
            content: 'test if the Current Year Unallocated Earnings line is present (but the value is 0)',
            trigger: '.line_name:contains("Current Year Unallocated Earnings")',
        },
        {
            content: 'test if the Unallocated Earnings line is present (but value is different from 0 and so should be there after the hide_0_lines',
            trigger: '.line_name:contains("Unallocated Earnings")',
        },
        {
            content: "Open options selector",
            trigger: "#filter_extra_options button",
            run: 'click',
        },
        {
            content: "Select the hide line at 0 option",
            trigger: ".dropdown-item:contains('Hide lines at 0')",
            run: 'click',
        },
        {
            content: 'test if the Unallocated Earnings line is still present',
            trigger: '.line_name:contains("Unallocated Earnings")',
        },
        {
            content: 'test if the Bank and Cash line is not present',
            trigger: '.line_name:not(:contains("Bank and Cash Accounts"))',
        },
        {
            content: 'test if the Current Year Unallocated Earnings line is not present',
            trigger: '.line_name:not(:contains("Current Year Unallocated Earnings"))',
        },
        {
            content: "Click again to open the options selector",
            trigger: "#filter_extra_options button",
            run: 'click',
        },
        {
            content: "Select the hide lines at 0 option again",
            trigger: ".dropdown-item:contains('Hide lines at 0')",
            run: 'click',
        },
        {
            content: 'test again if the Bank and Cash line is present (but the value is 0)',
            trigger: '.line_name:contains("Bank and Cash Accounts")',
            run: () => null,
        },
    ]
});
