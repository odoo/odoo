/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('account_reports_hide_0_lines', {
    url: '/odoo/action-account_reports.action_account_report_bs',
    steps: () => [
        {
            content: 'test if the Bank and Cash line is present (but the value is 0)',
            trigger: '.line_name:contains("Bank and Cash Accounts")',
            run: "click",
        },
        {
            content: 'test if the Current Year Unallocated Earnings line is present (but the value is 0)',
            trigger: '.line_name:contains("Current Year Unallocated Earnings")',
            run: "click",
        },
        {
            content: 'test if the Unallocated Earnings line is present (but value is different from 0 and so should be there after the hide_0_lines',
            trigger: '.line_name:contains("Unallocated Earnings")',
            run: "click",
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
            run: "click",
        },
        {
            content: 'test if the Bank and Cash line is not present',
            trigger: '.line_name:not(:contains("Bank and Cash Accounts"))',
            run: "click",
        },
        {
            content: 'test if the Current Year Unallocated Earnings line is not present',
            trigger: '.line_name:not(:contains("Current Year Unallocated Earnings"))',
            run: "click",
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

registry.category("web_tour.tours").add('account_reports_hide_0_lines_with_string_columns', {
    url: '/odoo/action-account_reports.action_account_report_general_ledger',
    steps: () => [
        {
            content: "Check if the 211000 Account Payable line is present (but the value is 0)",
            trigger: ".name:contains('211000 Account Payable')",
            run: "click",
        },
        {
            content: "Check if the MISC item line is present with string values set up, but all amounts are at 0",
            trigger: ".name:contains('Coucou les biloutes')",
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
            content: "Check if the MISC item line is hidden",
            trigger: ":not(:visible):contains('Coucou les biloutes')",
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
            content: "Check again if the MISC item line is present (but the value is 0)",
            trigger: ".name:contains('Coucou les biloutes')",
        },
    ]
});

registry.category("web_tour.tours").add('account_reports_hide_0_lines_load_more', {
    url: '/odoo/action-account_reports.action_account_report_general_ledger',
    steps: () => [
        {
            content: "Check if the 211000 Account Payable line is present (but the value is 0)",
            trigger: ".name:contains('211000 Account Payable')",
            run: "click",
        },
        {
            content: "Check if the MISC item line is present with string values set up, but all amounts are at 0",
            trigger: ".name:contains('Coucou les biloutes 0')",
        },
        {
            content: "Check if the Load more line is present",
            trigger: ".clickable:contains('Load more')",
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
            content: "Check if the Load more line is still present",
            trigger: ".clickable:contains('Load more')",
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
            content: "Check if the first MISC item line is present with string values set up, but all amounts are at 0",
            trigger: ".name:contains('Coucou les biloutes 0')",
        },
        {
            content: "Check if the Load more line is present",
            trigger: ".clickable:contains('Load more')",
            run: 'click',
        },
        {
            content: "Check if the second MISC item line is present with string values set up, but all amounts are at 0",
            trigger: ".name:contains('Coucou les biloutes 1')",
        },
    ]
});
