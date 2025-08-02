import { registry } from "@web/core/registry";
import {
    freezeDateTime,
    selectPOVendor,
    selectPOWarehouse,
    goToCatalogFromPO,
    goToPOFromCatalog,
    toggleSuggest,
    setSuggestParameters,
} from "./tour_helpers";

registry.category("web_tour.tours").add("test_purchase_catalog_suggest_search", {
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
        toggleSuggest(),
        { trigger: "button[name='toggle_suggest_catalog'].fa-toggle-off" },
        {
            content: "Check suggest fields hidden when suggest is off",
            trigger: ".o_kanban_view.o_purchase_product_kanban_catalog_view",
            run() {
                const selectors = [
                    ".o_TimePeriodSelectionField",
                    "input.o_PurchaseSuggestInput",
                    ".o_purchase_suggest_footer",
                ];
                const stillVisible = selectors.some((sel) => {
                    const el = document.querySelector(sel);
                    return el && el.offsetParent !== null;
                });
                if (stillVisible) {
                    throw new Error("Toggle did not hide elements");
                }
            },
        },
        ...goToPOFromCatalog(),
        ...goToCatalogFromPO(),
        { trigger: "button[name='toggle_suggest_catalog'].fa-toggle-off" }, // Should still be off
        toggleSuggest(),
        { trigger: "button[name='toggle_suggest_catalog'].fa-toggle-on" },
        ...setSuggestParameters({ basedOn: "Last 3 months", nbDays: 90, factor: 100, wait: 1000 }),
        {
            trigger: "span[name='suggest_total']",
            async run() {
                await new Promise((r) => setTimeout(r, 1000));
                const total = parseFloat(this.anchor.textContent);
                if (total !== 0) {
                    throw new Error(`Expected suggest_total = 0, got ${total} (wrong warehouse)`);
                }
            },
        },
        ...goToPOFromCatalog(),
        ...selectPOWarehouse("Base Warehouse: Receipts"), // Still the same PO, no need to reset vendor
        ...goToCatalogFromPO(),
        { trigger: ".o_kanban_view.o_purchase_product_kanban_catalog_view" },
        { trigger: "button[name='toggle_suggest_catalog'].fa-toggle-on" }, // Should still be ON
        ...setSuggestParameters({ basedOn: "Last 7 days", nbDays: 28, factor: 50, wait: 1000 }),
        {
            trigger: "span[name='suggest_total']",
            async run() {
                await new Promise((r) => setTimeout(r, 1000));
                const total = parseFloat(this.anchor.textContent);
                if (total !== 480) {
                    throw new Error(`Expected suggest_total = 480, got ${total}`);
                }
            },
        }, // Now for the correct WH suggest should be 12 units/week * 4 weeks * 20$/ unit * 50% = 480$
        {
            content: "Add all suggestion to the PO",
            trigger: 'button[name="suggest_add_all"]',
            run: "click",
        }, // Should save suggest params when "ADD ALL"
        ...goToPOFromCatalog(),
        {
            content: "Check suggest_test was added to PO",
            trigger: "div.o_field_product_label_section_and_note_cell span",
            run() {
                const first_prod = this.anchor.textContent.trim();
                if (!first_prod.includes("suggest_test")) {
                    throw new Error("Expected product to be added to PO");
                }
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
                const value = parseInt(this.anchor.value);
                if (value !== 28) {
                    throw new Error(`Expected days to be saved to 28 got ${value}`);
                }
            },
        },
        {
            content: "Check percent factor saved",
            trigger: "input.o_PurchaseSuggestInput:eq(1)",
            run() {
                const value = parseInt(this.anchor.value);
                if (value !== 50) {
                    throw new Error(`Expected percent factor to be saved to 50% got ${value}%`);
                }
            },
        },
        {
            content: "Check based on saved",
            trigger: ".o_TimePeriodSelectionField",
            run() {
                const input = this.anchor.querySelector(".o_select_menu_toggler");
                if (input.value !== "Last 7 days") {
                    throw new Error(`Expected based on to be "Last 7 days" got ${input.value}`);
                }
            },
        },
        ...setSuggestParameters({ basedOn: "Actual Demand", wait: 1000 }), // Keeping factor 50%
        {
            content: "Check the expected total suggest price match expectations",
            trigger: "span[name='suggest_total']",
            run() {
                const total = parseFloat(this.anchor.textContent);
                if (total !== 1000) {
                    throw new Error(`Expected suggest_total = 1000, got ${total}`);
                }
            },
        }, // Suggest total should be -100 units forcasted * 50% * 20 = 1000$
        {
            content: "Go back to the dashboard",
            trigger: ".o_menu_brand",
            run: "click",
        },
    ],
});
