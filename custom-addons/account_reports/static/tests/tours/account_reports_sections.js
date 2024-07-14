/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('account_reports_sections', {
    test: true,
    url: "/web?#action=account_reports.action_account_report_gt",
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
            run: function(){},
        },
        {
            content: "Check the columns of section 1 are displayed",
            trigger: "#table_header th:last():contains('Column 1')",
            run: function(){},
        },
        {
            content: "Check the export buttons belong to the composite report",
            trigger: ".btn:contains('composite_report_custom_button')",
            run: function(){},
        },
        {
            content: "Check the filters displayed belong to section 1 (journals filter is not enabled on section 2, nor the composite report)",
            trigger: "#filter_journal",
            run: function(){},
        },
        {
            content: "Check the date chosen by default",
            trigger: "#filter_date button:contains('2023')",
            run: function(){},
        },
        {
            content: "Switch to section 2",
            trigger: "#section_selector .btn:contains('Section 2')",
            run: 'click',
        },
        {
            content: "Check the lines of section 2 are displayed",
            trigger: ".line_name:contains('Section 2 line')",
            run: function(){},
        },
        {
            content: "Check the columns of section 2 are displayed",
            trigger: "#table_header th:last():contains('Column 2')",
            run: function(){},
        },
        {
            content: "Check the export buttons belong to the composite report",
            trigger: ".btn:contains('composite_report_custom_button')",
            run: function(){},
        },
        {
            content: "Check the filters displayed belong to section 2 (comparison filter is not enabled on section 1, nor the composite report)",
            trigger: "#filter_comparison",
            run: function(){},
        },
        {
            content: "Open date switcher",
            trigger: "#filter_date button",
            run: 'click',
        },
        {
            content: "Select another date",
            trigger: "#filter_date span:contains('Last Financial Year')",
            run: 'click'
        },
        {
            content: "Wait for refresh",
            trigger: "#filter_date button:contains('2022')",
            run: function(){},
        },
        {
            content: "Switch back to section 1",
            trigger: "#section_selector .btn:contains('Section 1')",
            run: 'click',
        },
        {
            content: "Check the date chosen on section 2 has been propagated to section 1",
            trigger: "#filter_date button:contains('2022')",
            run: function(){},
        },
    ]
});
