/** @odoo-module **/

import { registry } from "@web/core/registry";
import { TourError } from "@web_tour/tour_service/tour_utils";

function assert(current, expected, info) {
    if (current !== expected) {
        fail(info + ': "' + current + '" instead of "' + expected + '".');
    }
}

function fail(errorMessage) {
    throw new TourError(errorMessage);
}

const SHEETNAME = "Res Partner Test Spreadsheet";
registry.category("web_tour.tours").add("spreadsheet_open_pivot_sheet", {
    test: true,
    steps: () => [
        {
            trigger: '.o_app[data-menu-xmlid="documents.menu_root"]',
            content: "Open document app",
            run: "click",
        },
        {
            trigger: 'li[title="Test folder"] header',
            content: "Open the test folder",
            run: "click",
        },
        {
            trigger: `div[title="${SHEETNAME}"]`,
            content: "Select Test Sheet",
            run: "click",
        },
        {
            trigger: `button.o_switch_view.o_list`,
            content: "Switch to list view",
            run: "click",
        },
        {
            trigger: `img[title="${SHEETNAME}"]`,
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
                    pivot.querySelector("div.o_side_panel_title").textContent,
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
            trigger: '[data-menu-xmlid="documents.dashboard"]',
            content: "Go back to Document App",
        },
        {
            trigger: ".o_document_spreadsheet:first",
            content: "Sheet is visible in Documents",
            isCheck: true,
        },
    ],
});
