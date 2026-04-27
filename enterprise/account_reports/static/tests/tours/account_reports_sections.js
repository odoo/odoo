/** @odoo-module **/

const { DateTime } = luxon;

import { Asserts } from "./asserts";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('account_reports_sections', {
    url: "/odoo/action-account_reports.action_account_report_gt",
    steps: () => [
        {
            content: "Open variant selector",
            trigger: "#filter_variant button",
            run: 'click',
        },
        {
            content: "Select the test variant using sections",
            trigger: ".dropdown-item:contains('Test Sections')",
            run: 'click',
        },
        {
            content: "Check the lines of section 1 are displayed",
            trigger: ".line_name:contains('Section 1 line')",
        },
        {
            content: "Check the columns of section 1 are displayed",
            trigger: "#table_header th:last():contains('Column 1')",
        },
        {
            content: "Check the export buttons belong to the composite report",
            trigger: ".btn:contains('composite_report_custom_button')",
        },
        {
            content: "Check the filters displayed belong to section 1 (journals filter is not enabled on section 2, nor the composite report)",
            trigger: "#filter_journal",
        },
        {
            content: "Check the date chosen by default",
            trigger: "#filter_date",
            run: (actionHelper) => {
                // Generic tax report opens on the previous period and in this case the period is one month.
                // And since we are using the generic tax report, we need to go back one month.
                const previousMonth = DateTime.now().minus({months: 1});

                Asserts.isTrue(actionHelper.anchor.getElementsByTagName('button')[0].innerText.includes(previousMonth.year));
            },
        },
        {
            content: "Switch to section 2",
            trigger: "#section_selector .btn:contains('Section 2')",
            run: 'click',
        },
        {
            content: "Check the lines of section 2 are displayed",
            trigger: ".line_name:contains('Section 2 line')",
        },
        {
            content: "Check the columns of section 2 are displayed",
            trigger: "#table_header th:last():contains('Column 2')",
        },
        {
            content: "Check the export buttons belong to the composite report",
            trigger: ".btn:contains('composite_report_custom_button')",
        },
        {
            content: "Check the filters displayed belong to section 2 (comparison filter is not enabled on section 1, nor the composite report)",
            trigger: "#filter_comparison",
        },
        {
            content: "Open date switcher",
            trigger: "#filter_date button",
            run: 'click',
        },
        {
            content: "Select another date in the future",
            trigger: ".dropdown-menu span.dropdown-item:nth-child(3) .btn_next_date",
            run: 'click'
        },
        {
            content: "Apply filter by closing the dropdown for the future date",
            trigger: "#filter_date .btn:first()",
            run: "click",
        },
        {
            content: "Check that the date has changed",
            trigger: `#filter_date button:not(:contains(${ DateTime.now().minus({months: 1}).year }))`, // We need to remove one month for the case where we are in january. It will impact the year.
            run: (actionHelper) => {
                const nextYear = DateTime.now().plus({years: 1}).year;

                Asserts.isTrue(actionHelper.anchor.innerText.includes(nextYear));
            },
        },
        {
            content: "Open date switcher",
            trigger: "#filter_date button",
            run: 'click',
        },
        {
            content: "Select another date first time",
            trigger: ".dropdown-menu span.dropdown-item:nth-child(3) .btn_previous_date",
            run: 'click'
        },
        {
            trigger: `.dropdown-menu span.dropdown-item:nth-child(3) time:contains(${ DateTime.now().year})`,
        },
        {
            content: "Select another date second time",
            trigger: ".dropdown-menu span.dropdown-item:nth-child(3) .btn_previous_date",
            run: 'click'
        },
        {
            trigger: `.dropdown-menu span.dropdown-item:nth-child(3) time:contains(${ DateTime.now().minus({years: 1}).year })`,
        },
        {
            content: "Apply filter by closing the dropdown",
            trigger: "#filter_date .btn:first()",
            run: "click",
        },
        {
            content: "Check that the date has changed",
            trigger: `#filter_date button:contains(${ DateTime.now().minus({years: 1}).year })`,
        },
        {
            content: "Switch back to section 1",
            trigger: "#section_selector .btn:contains('Section 1')",
            run: 'click',
        },
    ]
});
