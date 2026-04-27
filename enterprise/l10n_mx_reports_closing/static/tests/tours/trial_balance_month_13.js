/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Asserts } from "../../../../account_reports/static/tests/tours/asserts";

registry.category("web_tour.tours").add("trial_balance_month_13_date_filter", {
    url: "/odoo/action-account_reports.action_account_report_coa",
    steps: () => [
        //--------------------------------------------------------------------------------------------------------------
        // Foldable
        //--------------------------------------------------------------------------------------------------------------
        {
            content: "Open date filter",
            trigger: "#filter_date button",
            run: "click",
        },
        {
            content: "Select Month 13",
            trigger: ".filter_name:contains('Month 13')",
            run: "click",
        },
        {
            content: "Check that no other date is selected",
            trigger: ".date_filter.selected .filter_name:contains('Month 13')",
            run: () => {
                Asserts.DOMContainsNumber(".date_filter.selected", 1);
            },
        },
        {
            content: "Apply filter by closing the dropdown for the future date",
            trigger: "#filter_date .btn:first()",
            run: "click",
        },
        {
            content: "Check that the report has changed to display the Month 13",
            trigger: ".column_header:contains('Month 13')",
        },
        {
            content: "Check that the values have been correctly computed",
            trigger: "tr:contains('3 Stockholders') div.name:contains('250.0')",
        },
        {
            content: "Open date filter",
            trigger: "#filter_date button",
            run: "click",
        },
        {
            content: "Change to a different date",
            trigger: ".filter_name:contains('Year')",
            run: "click",
        },
        {
            content: "Apply filter by closing the dropdown for the future date",
            trigger: "#filter_date .btn:first()",
            run: "click",
        },
        {
            content: "The report should not display the Month 13 anymore",
            trigger: "#table_header>tr:nth-child(1) th:nth-child(3):not(:contains('Month 13'))",
        },
        {
            content: "Check that the values have changed back for the year without Month 13",
            trigger: "tr:contains('3 Stockholders') div.name:contains('0.0')",
        },
    ],
});
