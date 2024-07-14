/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('account_reports_widgets', {
    test: true,
    url: '/web?#action=account_reports.action_account_report_pl',
    steps: () => [
        {
            content: "change date filter",
            trigger: "#filter_date button",
            run: 'click',
        },
        {
            content: "change date filter",
            trigger: "#filter_date span:contains('Last Financial Year')",
            run: 'click'
        },
        {
            content: "wait refresh",
            trigger: "#filter_date button:contains('2019')",
        },
        {
            content: "change comparison filter",
            trigger: "#filter_comparison .btn:first()",
            run: 'click',
        },
        {
            content: "wait for Apply button and click on it",
            trigger: "#filter_comparison .dropdown-menu .btn:first()",
            run: 'click',
        },
        {
            content: "wait refresh, report should have 4 columns",
            trigger: "th + th + th + th",
            run: function(){},
        },
        {
            title: "open dropdown",
            trigger: ".o_control_panel_main_buttons .dropdown-toggle",
            run: 'click',
        },
        {
            title: "export xlsx",
            trigger: "button:contains('XLSX')",
            run: 'click'
        },
    ]
});
