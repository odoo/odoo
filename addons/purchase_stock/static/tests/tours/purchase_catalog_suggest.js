import { registry } from "@web/core/registry";
import { assert } from "@stock/../tests/tours/tour_helper";
import {
    freezeDateTime,
    selectPOVendor,
    selectPOWarehouse,
    goToCatalogFromPO,
    goToPOFromCatalog,
    toggleSuggest,
    setSuggestParameters,
} from "./tour_helpers";

registry.category("web_tour.tours").add("test_purchase_order_suggest_search_panel_ux", {
    steps: () => [
        ...freezeDateTime("2021-01-14 09:12:15"), // Same date as python @freeze decorator
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
        { trigger: "button[name='toggle_suggest_catalog'].fa-toggle-off" }, // Should still be off
        ...toggleSuggest(true),
        ...setSuggestParameters({ basedOn: "Last 3 months", nbDays: 90, factor: 100 }),
        {
            content: "Check on warehouse2 should only be taking those stock move into account",
            trigger: "span[name='suggest_total']:visible",
            run() {
                const estimatedTotal = this.anchor.textContent.trim();
                assert(estimatedTotal, "20", `Wrong suggest estimated total price`);
            },
        },
        ...goToPOFromCatalog(),
        ...selectPOWarehouse("Base Warehouse: Receipts"), // Still the same PO, no need to reset vendor
        ...goToCatalogFromPO(),
        { trigger: ".o_kanban_view.o_purchase_product_kanban_catalog_view" },
        { trigger: "button[name='toggle_suggest_catalog'].fa-toggle-on" }, // Should still be ON
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
                assert(days, 28, `Suggest number of days value not saved for vendor`);
            },
        },
        {
            content: "Check percent factor saved",
            trigger: "input.o_PurchaseSuggestInput:eq(1)",
            run() {
                const percent = parseInt(this.anchor.value);
                assert(percent, 50, `Suggest Percent factor value not saved for vendor`);
            },
        },
        {
            content: "Check based on saved",
            trigger: ".o_TimePeriodSelectionField",
            run() {
                const i = this.anchor.querySelector(".o_select_menu_toggler");
                assert(i.value, "Last 7 days", `Suggest Based on value not saved for vendor`);
            },
        },
        ...setSuggestParameters({ basedOn: "Actual Demand" }), // Keeping factor 50%
        // Suggest total should be -100 units forcasted * 50% * 20 = 1000$
        { trigger: "span[name='suggest_total']:visible:contains('1000')" },
        {
            content: "Go back to the dashboard",
            trigger: ".o_menu_brand",
            run: "click",
        },
    ],
});
