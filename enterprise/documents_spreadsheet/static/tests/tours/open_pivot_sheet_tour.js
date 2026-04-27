/** @odoo-module **/

import { registry } from "@web/core/registry";

function assert(current, expected, info) {
    if (current !== expected) {
        fail(info + ': "' + current + '" instead of "' + expected + '".');
    }
}

function fail(errorMessage) {
    console.error(errorMessage);
}

const SHEETNAME = "Res Partner Test Spreadsheet";
registry.category("web_tour.tours").add("spreadsheet_open_pivot_sheet", {
    steps: () => [
        {
            trigger: '.o_app[data-menu-xmlid="documents.menu_root"]',
            content: "Open document app",
            run: "click",
        },
        {
            trigger: '.o_documents_title:contains("Folders")',
            content: "check if the folders are loaded",
        },
        {
            trigger: 'li[title="Company"] header button',
            content: "Open the company folder",
            run: "click",
        },
        {
            trigger: "span.o_search_panel_label_title:contains('Test Folder')",
            content: "Open the test folder (in company folder)",
            run: "click",
        },
        {
            trigger: `button.o_switch_view.o_list`,
            content: "Switch to list view",
            run: "click",
        },
        {
            trigger: `.o_data_cell:contains("${SHEETNAME}")`,
            content: "Open the sheet",
            run: "click",
        },
        {
            trigger: "div.o_topbar_filter_icon",
            content: "Open Filters",
            run: "click",
        },
        {
            trigger: "div.pivot_filter",
            content: "",
            run: function (actions) {
                const pivots = document.querySelectorAll("div.pivot_filter");
                assert(pivots.length, 1, "There should be one filter");
                const pivot = pivots[0];
                assert(
                    pivot.querySelector("span.o_side_panel_filter_label").textContent,
                    "MyFilter1",
                    "Invalid filter name"
                );
                assert(
                    Boolean(
                        pivot.querySelector(
                            'div.o_multi_record_selector span.badge[title="AdminDude"]'
                        )
                    ),
                    true,
                    "Wrong default filter value"
                );
                actions.click(pivot.querySelector(".o_side_panel_filter_icon.fa-cog"));
            },
        },
        {
            trigger: ".o_spreadsheet_filter_editor_side_panel",
            content: "Check filter values",
            run: function () {
                const defaultFilterValue = document.querySelectorAll(
                    'div.o_multi_record_selector span.badge[title="AdminDude"]'
                );
                assert(
                    defaultFilterValue.length,
                    1,
                    "There should be a default value in the filter..."
                );
                assert(
                    document.querySelector(".o_side_panel_related_model input").value,
                    "User",
                    "Wrong model selected"
                );

                const fieldsValue = document.querySelector(
                    "div.o_model_field_selector_value span.o_model_field_selector_chain_part"
                );
                assert(fieldsValue.textContent.trim(), "Users");
            },
        },
        {
            trigger: ".o-sp-breadcrumb",
            content: "Go back to Document App",
            run: "click",
        },
        {
            trigger: `.o_data_cell:contains("${SHEETNAME}")`,
            content: "Sheet is visible in Documents",
        },
    ],
});
