/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("account_reports_analytic_filters", {
    url: "/odoo/action-account_reports.action_account_report_general_ledger",
    steps: () => [
        {
            content: "click analytic filters",
            trigger: ".filter_analytic button",
            run: "click",
        },
        {
            content: "insert text in the searchbar",
            trigger: ".o_multi_record_selector input",
            run: "edit Time",
        },
        {
            content: "click on the item",
            trigger: '.o-autocomplete--dropdown-item:contains("Time Off")',
            run: "click",
        },
        {
            content: "Check the label of the badge",
            trigger: '.dropdown-menu .o_tag_badge_text:contains("Time Off")',
        },
    ],
});
