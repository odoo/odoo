import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("account_reports_widgets", {
    url: "/odoo/action-account_reports.action_account_report_pl",
    steps: () => [
        {
            content: "change date filter",
            trigger: "#filter_date button",
            run: "click",
        },
        {
            content: "Select another date in the future",
            trigger: ".dropdown-menu span.dropdown-item:nth-child(3) .btn_next_date",
            run: 'click'
        },
        {
            content: "Apply filter by closing the dropdown",
            trigger: "#filter_date .btn:first()",
            run: "click",
        },
        {
            content: "wait refresh",
            trigger: `#filter_date button:not(:contains(${ new Date().getFullYear() }))`,
        },
        {
            content: "change date filter for the second time",
            trigger: "#filter_date button",
            run: "click",
        },
        {
            content: "Select another date in the past first time",
            trigger: ".dropdown-menu span.dropdown-item:nth-child(3) .btn_previous_date",
            run: 'click'
        },
        {
            trigger: `.dropdown-menu span.dropdown-item:nth-child(3) time:contains(${new Date().getFullYear()})`,
        },
        {
            content: "Select another date in the past second time",
            trigger: ".dropdown-menu span.dropdown-item:nth-child(3) .btn_previous_date",
            run: 'click'
        },
        {
            trigger: `.dropdown-menu span.dropdown-item:nth-child(3) time:contains(${
                new Date().getFullYear() - 1
            })`,
        },
        {
            content: "Apply filter by closing the dropdown",
            trigger: "#filter_date .btn:first()",
            run: "click",
        },
        {
            content: "wait refresh",
            trigger: `#filter_date button:contains(${ new Date().getFullYear() - 1 })`,
        },
        {
            content: "change comparison filter",
            trigger: "#filter_comparison .btn:first()",
            run: "click",
        },
        {
            content: "change comparison filter",
            trigger: ".dropdown-item.period:first()",
            run: "click",
        },
        {
            content: "Apply filter by closing the dropdown",
            trigger: "#filter_comparison .btn:first()",
            run: "click",
        },
        {
            content: "wait refresh, report should have 4 columns",
            trigger: "th + th + th + th",
        },
        {
            content: "export xlsx",
            trigger: "button:contains('XLSX')",
            run: "click",
        },
    ],
});
