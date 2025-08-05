import { registry } from "@web/core/registry";
import { assert } from "@stock/../tests/tours/tour_helper";
import {
    goToCatalogFromPO,
    goToPOFromCatalog,
    toggleSuggest,
    setSuggestParameters,
    checkKanbanRecordHighlight,
} from "./tour_helper";
import { selectPOVendor, selectPOWarehouse } from "@purchase/../tests/tours/tour_helper";

/**
 * Checks that the Suggest UI in the search panel works well
 * (estimated price, warehouse logic, toggling, saving defaults)
 */
registry.category("web_tour.tours").add("test_purchase_order_suggest_search_panel_ux", {
    steps: () => [
        /*
         * -----------------  PART 1 : Suggest Component -----------------
         * Checks that the Suggest UI in the search panel works well
         * (estimated price, warehouse logic, toggling, saving defaults)
         * ----------------------------------------------------------------
         */
        { trigger: ".o_purchase_order" },
        {
            content: "Create a New PO",
            trigger: ".o_list_button_add",
            run: "click",
        },
        ...selectPOVendor("Julia Agrolait"),
        ...goToCatalogFromPO(),
        ...toggleSuggest(false),
        {
            content: "Check suggest fields hidden when suggest is off",
            trigger: ".o_kanban_view.o_purchase_product_kanban_catalog_view",
            run() {
                const els = document.querySelectorAll(
                    ".o_TimePeriodSelectionField, input.o_PurchaseSuggestInput, .o_purchase_suggest_footer"
                );
                assert(els.length, 0, "Toggle did not hide elements");
            },
        },
        ...goToPOFromCatalog(),
        ...goToCatalogFromPO(),
        { trigger: 'div[name="search-suggest-toggle"] input:not(:checked)' }, // Should still be off
        ...toggleSuggest(true),
        ...setSuggestParameters({ basedOn: "Last 3 months", nbDays: 90, factor: 100 }),
        { trigger: "span[name='suggest_total']:visible:contains('$ 20.00')" },
        ...goToPOFromCatalog(),
        ...selectPOWarehouse("Base Warehouse: Receipts"), // Still the same PO, no need to reset vendor
        ...goToCatalogFromPO(),
        { trigger: ".o_kanban_view.o_purchase_product_kanban_catalog_view" },
        { trigger: 'div[name="search-suggest-toggle"] input:checked' }, // Should still be ON
        ...setSuggestParameters({ basedOn: "Last 7 days", nbDays: 28, factor: 50 }),
        // Now for the correct WH suggest should be 12 units/week * 4 weeks * 20$/ unit * 50% = 480$
        { trigger: "span[name='suggest_total']:visible:contains('480')" },
        {
            content: "Add all suggestion to the PO",
            trigger: 'button[name="suggest_add_all"]',
            run: "click",
        }, // Should save suggest params when "ADD ALL"
        ...goToPOFromCatalog(),
        {
            content: "Check test_product was added to PO",
            trigger: "div.o_field_product_label_section_and_note_cell span",
            run() {
                const order_line = this.anchor.textContent.trim();
                assert(order_line.includes("test_product"), true, `Product not added to PO`);
            },
        },
        {
            content: "Create a New PO",
            trigger: ".o_form_button_create",
            run: "click",
        },
        { trigger: ".o_form_view.o_purchase_order" },
        ...selectPOVendor("Julia Agrolait"),
        ...selectPOWarehouse("Base Warehouse: Receipts"),
        ...goToCatalogFromPO(),
        {
            content: "Check number days saved",
            trigger: "input.o_PurchaseSuggestInput:eq(0)",
            run() {
                const days = parseInt(this.anchor.value);
                assert(days, 28, `Expected days to be saved to 28, but got ${days}`);
            },
        },
        {
            content: "Check percent factor saved",
            trigger: "input.o_PurchaseSuggestInput:eq(1)",
            run() {
                const percent = parseInt(this.anchor.value);
                assert(percent, 50, `Expected percent factor to be saved to 50% got ${percent}`);
            },
        },
        {
            content: "Check based on saved",
            trigger: ".o_TimePeriodSelectionField",
            run() {
                const i = this.anchor.querySelector(".o_select_menu_toggler");
                assert(i.value, "Last 7 days", `based_on = ${i.value},should be "Last 7 days"`);
            },
        },
        ...setSuggestParameters({ basedOn: "Actual Demand", nbDays: 30, factor: 50 }),
        // Suggest total should be -100 units forcasted * 50% * 20 = 1000$
        { trigger: "span[name='suggest_total']:visible:contains('1,000')" },
        /*
         * -----------------  PART 2 : Kanban Interactions -----------------
         * Checks that the Suggest UI and the Kanban record interactions
         * (monthly demand, suggest_qtys, ADD suggested qtys)
         * TODO: filtering attributes and categories (including Group by)
         * TODO: Check monthly demand and Suggested qty when changing warehouse
         * ------------------------------------------------------------------
         */
        ...setSuggestParameters({ basedOn: "Last 7 days", nbDays: 28, factor: 50 }),
        { trigger: "span[name='suggest_total']:visible:contains('480')" },
        { trigger: "span[name='o_kanban_monthly_demand_qty']:visible:contains('52')" }, // ceil(12 * 30/ 7)
        { trigger: "div[name='o_kanban_purchase_suggest'] span:visible:contains('24')" }, // 12 * 4 * 50%
        checkKanbanRecordHighlight("test_product", 1),

        ...setSuggestParameters({ basedOn: "Last 30 days" }),
        { trigger: "span[name='suggest_total']:visible:contains('240')" },
        { trigger: "span[name='o_kanban_monthly_demand_qty']:visible:contains('24')" }, // 2 orders of 12
        { trigger: "div[name='o_kanban_purchase_suggest'] span:visible:contains('12')" }, // 24 * 1 (28 days ~= 1 month) * 50% = 12

        ...setSuggestParameters({ basedOn: "Last 3 months" }),
        { trigger: "span[name='suggest_total']:visible:contains('80')" },
        { trigger: "span[name='o_kanban_monthly_demand_qty']:visible:contains('8')" }, // 24 / 3 = 8 with quaterly
        { trigger: "div[name='o_kanban_purchase_suggest'] span:visible:contains('4')" }, // 24 / 3* 1 (28 days ~= 1 month) * 50% = 4
        ...toggleSuggest(false),
        { trigger: "span[name='o_kanban_monthly_demand_qty']:visible:contains('24')" }, // Should come back to normal monthly demand
        checkKanbanRecordHighlight("test_product", 1, false), // expected order 1 not checked, just that highligh is off
        ...toggleSuggest(true),

        ...setSuggestParameters({ basedOn: "Actual Demand", factor: 100 }),
        { trigger: "span[name='suggest_total']:visible:contains('2,000')" },
        { trigger: "span[name='o_kanban_forecasted_qty']:visible:contains('100')" }, // Move out of 100 in 20days
        { trigger: "div[name='o_kanban_purchase_suggest'] span:visible:contains('100')" }, // 100 * 100%
        ...setSuggestParameters({ factor: 200 }),
        { trigger: "div[name='o_kanban_purchase_suggest'] span:visible:contains('200')" }, // 100 * 200%
        ...setSuggestParameters({ factor: 50 }),
        { trigger: "div[name='o_kanban_purchase_suggest'] span:visible:contains('50')" }, // 100 * 50%
        {
            content: "Go back to the dashboard",
            trigger: ".o_menu_brand",
            run: "click",
        },
    ],
});

/**
 * TODO Create a TEST for actions Add all and adding individual products
 * With Mulitple warehouses, clicking twice on Add All ...
 */
