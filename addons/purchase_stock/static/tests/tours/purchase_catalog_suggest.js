import { registry } from "@web/core/registry";
import { assert, freezeDateTime } from "@stock/../tests/tours/tour_helper";
import {
    goToCatalogFromPO,
    goToPOFromCatalog,
    toggleSuggest,
    setSuggestParameters,
    checkKanbanRecordPosition,
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
        ...freezeDateTime("2021-01-14 09:12:15"),
        { trigger: ".o_purchase_order" },
        {
            content: "Create a New PO",
            trigger: ".o_list_button_add",
            run: "click",
        },
        ...selectPOVendor("Julia Agrolait"),
        ...goToCatalogFromPO(),
        {
            content: "Checks suggest is off by default and suggest fields hidden when suggest off",
            trigger: ".o_kanban_view.o_purchase_product_kanban_catalog_view",
            run() {
                const els = document.querySelectorAll(
                    ".o_TimePeriodSelectionField, input.o_PurchaseSuggestInput, .o_purchase_suggest_footer"
                );
                assert(els.length, 0, "Toggle did not hide elements");
            },
        },
        ...goToPOFromCatalog(),
        { trigger: ".o_purchase_order" },
        {
            content: "Confirm PO (one step vs Send RFQ)",
            trigger: 'button[name="button_confirm"]',
            run: "click",
        },
        ...goToCatalogFromPO(),
        // Suggest should not show on non draft POs
        { trigger: 'body:not(:has(div[name="search_panel_suggestion"]' },
        ...goToPOFromCatalog(),
        {
            content: "Cancel PO (to reset to draft)",
            trigger: 'button[name="button_cancel"]',
            run: "click",
        },
        {
            content: "Reset to draft",
            trigger: 'button[name="button_draft"]',
            run: "click",
        },
        ...goToCatalogFromPO(),
        { trigger: 'div[name="search-suggest-toggle"] input:not(:checked)' }, // Should still be off
        ...toggleSuggest(true),
        {
            content: "Toggling Suggestion activates filter for products in PO or suggested",
            trigger: '.o_facet_value:contains("Suggested")', // Suggested
        },
        ...setSuggestParameters({ basedOn: "Last 3 months", nbDays: 90, factor: 100 }),
        { trigger: "span[name='suggest_total']:visible:contains('$ 20.00')" },
        ...goToPOFromCatalog(),
        ...selectPOWarehouse("Base Warehouse: Receipts"), // Still the same PO, no need to reset vendor
        ...goToCatalogFromPO(),
        { trigger: ".o_kanban_view.o_purchase_product_kanban_catalog_view" },
        { trigger: 'div[name="search-suggest-toggle"] input:checked' }, // Should still be ON
        ...setSuggestParameters({ basedOn: "Last 7 days", nbDays: 28, factor: 50 }),
        // Now for the correct WH suggest should be 12 units/week * 4 weeks * 20$/ unit * 50% = 480$
        { trigger: "span[name='suggest_total']:visible:contains('$ 480.00')" },
        {
            content: "Add all suggestion to the PO",
            trigger: 'button[name="suggest_add_all"]',
            run: "click",
        }, // Should save suggest params when "ADD ALL"
        ...goToPOFromCatalog(),
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
        ...setSuggestParameters({ basedOn: "Forecasted", nbDays: 30, factor: 50 }),
        // Suggest total should be -100 units forcasted * 50% * 20 = 1,000$
        { trigger: "span[name='suggest_total']:visible:contains('1,000')" },
        /*
         * -----------------  PART 2 : Kanban Interactions -----------------
         * Checks suggest and the Kanban record interactions (product.product model)
         * (monthly demand, suggest_qtys, button style change and ordering )
         * ------------------------------------------------------------------
         */
        ...setSuggestParameters({ basedOn: "Last 7 days", nbDays: 28, factor: 50 }),
        { trigger: "span[name='suggest_total']:visible:contains('480')" },
        { trigger: "span[name='kanban_monthly_demand_qty']:visible:contains('52')" }, // ceil(12 * 30/ 7)
        { trigger: "div[name='kanban_purchase_suggest'] span:visible:contains('24')" }, // 12 * 4 * 50%
        checkKanbanRecordPosition("test_product", 0),
        ...toggleSuggest(false),
        { trigger: "span[name='kanban_monthly_demand_qty']:visible:contains('24')" }, // Should come back to normal monthly demand
        { trigger: "div.o_product_catalog_buttons i.fa-shopping-cart:visible" }, // == wait for front end to sync (shopping carts only when not suggested)
        checkKanbanRecordPosition("Courage", 0), // Product with lowest ref number should be first, test product should be first anymore
        ...toggleSuggest(true),
        { trigger: ".o_product_catalog_buttons .btn:has(.o_catalog_card_suggest_add)" }, // Wait for UI to sync
        { trigger: "span[name='kanban_monthly_demand_qty']:visible:contains('52')" }, // Wait for UI to sync
        checkKanbanRecordPosition("test_product", 0),

        ...setSuggestParameters({ basedOn: "Last 30 days", factor: 10 }),
        { trigger: "span[name='suggest_total']:visible:contains('60')" },
        { trigger: "span[name='kanban_monthly_demand_qty']:visible:contains('24')" }, // 2 orders of 12
        { trigger: "div[name='kanban_purchase_suggest'] span:visible:contains('3')" }, // 24 * 28 days (~=1 month) * 10% = 2.3.. (rounded up)

        ...setSuggestParameters({ basedOn: "Last 3 months", factor: 500 }),
        { trigger: "span[name='suggest_total']:visible:contains('740')" },
        { trigger: "span[name='kanban_monthly_demand_qty']:visible:contains('7.94')" }, // 24 / 3 ~= 7.94  with quaterly
        { trigger: "div[name='kanban_purchase_suggest'] span:visible:contains('37')" }, // 7.94 * (28 days / 30.4) * 500%  = 36.5.. (rounded up)

        ...setSuggestParameters({ basedOn: "Forecasted", factor: 100 }),
        { trigger: "span[name='suggest_total']:visible:contains('2,000')" },
        { trigger: "span[name='o_kanban_forecasted_qty']:visible:contains('100')" }, // Move out of 100 in 20days
        { trigger: "div[name='kanban_purchase_suggest'] span:visible:contains('100')" }, // 100 * 100%
        ...setSuggestParameters({ nbDays: 7 }),
        { trigger: "span[name='suggest_total']:visible:contains('$ 0.00')" }, // Move out of 100 in 20days, so no suggest for 7 days
        { trigger: ".o_view_nocontent_smiling_face" }, // Should suggest no products
        /*
         * -------------------  PART 3 : KANBAN ACTIONS ---------------------
         * Checks suggest and kanban record interactions (purchase.order model)
         * (Add, remove and add all buttons)
         * ------------------------------------------------------------------
         */
        ...setSuggestParameters({ basedOn: "Last 7 days", nbDays: 28, factor: 50 }),
        {
            content: "Add suggestion from Record",
            trigger: ".o_product_catalog_buttons .btn:has(.o_catalog_card_suggest_add)",
            run: "click",
        },
        { trigger: ".fa-trash" }, // Wait till its added
        {
            content: "Check added qty matches expectations",
            trigger: ".o_product_catalog_quantity input",
            run() {
                assert(parseInt(this.anchor.value), 24); // 12 * 4 * 50%
            },
        },
        {
            content: "Remove product from purchase Order and wait for UI to sync",
            trigger: "div.o_tooltip_div_remove button",
            async run(actions) {
                await actions.click(
                    [...document.querySelectorAll("div.o_tooltip_div_remove button")].at(0)
                );
                await new Promise((r) => setTimeout(r, 1000));
            },
        },
        { trigger: "span[name='kanban_monthly_demand_qty']:visible:contains('52')" }, // Wait for UI to sync
        { trigger: ".o_product_catalog_buttons .btn:has(.o_catalog_card_suggest_add)" }, // Wait for remove to be synced
        {
            content: "Add all suggestion to the PO",
            trigger: 'button[name="suggest_add_all"]',
            run: "click",
        },
        { trigger: ".fa-trash" }, // Wait till its added
        {
            content: "Check added qty matches expecations",
            trigger: ".o_product_catalog_quantity input",
            run() {
                assert(parseInt(this.anchor.value), 24); // 12 * 4 * 50%
            },
        },
        { trigger: "div[name='kanban_purchase_suggest'] span:hidden" }, // If qty in PO match suggested we should hide the string
        {
            content: "Add on more qty to check if suggest reappears",
            trigger: "div.o_product_catalog_quantity i.fa-plus",
            run: "click",
        },
        { trigger: "div[name='kanban_purchase_suggest'] span:visible" }, // If qty in PO match suggested we should hide the string
        {
            content: "Remove product from purchase Order",
            trigger: "div.o_tooltip_div_remove button",
            async run(actions) {
                await actions.click(
                    [...document.querySelectorAll("div.o_tooltip_div_remove button")].at(0)
                );
            },
        },
        // Should go back to displaying suggested qtys
        { trigger: "span[name='kanban_monthly_demand_qty']:visible:contains('52')" },
        { trigger: "div[name='kanban_purchase_suggest'] span:visible:contains('24')" },
        checkKanbanRecordPosition("test_product", 0),
        /*
         * -------------------  PART 4 : KANBAN FILTERS ---------------------
         * Checks suggest and searchModel (filters) interactions
         * (Add / Remove with filters), TODO category filters
         * ------------------------------------------------------------------
         */
        // Remove suggest filter
        {
            content: "Remove the Suggested Or In Order filter",
            trigger: '.o_facet_value:contains("Suggested")',
            async run(actions) {
                await actions.click(
                    [...document.querySelectorAll(".o_searchview_facet")]
                        .at(-1)
                        .querySelector(".o_facet_remove")
                );
            },
        },
        ...toggleSuggest(false), // toggling with filter off should still deactivate suggest
        { trigger: "div.o_product_catalog_buttons i.fa-shopping-cart:visible" }, // == wait for front end to sync (shopping carts only when not suggested)
        checkKanbanRecordPosition("Courage", 0), // == suggest is off
        {
            content: "Add a non suggested product to order",
            trigger: "div.o_product_catalog_buttons i.fa-shopping-cart",
            run: "click",
        },
        ...toggleSuggest(true),
        { trigger: '.o_facet_value:contains("Suggested")' }, // 12 * 4 * 50%
        {
            content: "Remove non suggested product from purchase Order",
            trigger: "div.o_tooltip_div_remove button",
            async run(actions) {
                await actions.click(
                    [...document.querySelectorAll("div.o_tooltip_div_remove button")].at(0)
                );
                await new Promise((r) => setTimeout(r, 1000)); // Wait one second to catch a bug where record disappears and reappears
            },
        },
        {
            content: "Remove the Suggested filter",
            trigger: '.o_facet_value:contains("Suggested")',
            async run(actions) {
                await actions.click(
                    [...document.querySelectorAll(".o_searchview_facet")]
                        .at(-1)
                        .querySelector(".o_facet_remove")
                );
            },
        },
        { trigger: "div[name='kanban_purchase_suggest'] span:visible:contains('24')" },
        {
            content: "Add suggestion by clicking on the record",
            trigger: ".o_kanban_record",
            run: "click",
        },
        { trigger: ".fa-trash" }, // Wait till its added
        ...goToPOFromCatalog(),
        {
            content: "Check test_product was added to PO",
            trigger: "div.o_field_product_label_section_and_note_cell span",
            run() {
                const first_prod = this.anchor.textContent.trim();
                assert(first_prod.includes("test_product"), true, "product not added to PO");
            },
        }, // TODO IMPROVE: check qty
        {
            content: "Go back to the dashboard",
            trigger: ".o_menu_brand",
            run: "click",
        },
    ],
});
