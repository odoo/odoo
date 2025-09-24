import { registry } from "@web/core/registry";
import { assert } from "@stock/../tests/tours/tour_helper";
import { catalogSuggestion } from "./tour_helper";
import { purchaseForm, productCatalog } from "@purchase/../tests/tours/tour_helper";

registry.category("web_tour.tours").add("test_purchase_order_suggest_search_panel_ux", {
    steps: () => [
        /*
         * -----------------  PART 1 : Suggest Component -----------------
         * Checks that the Suggest UI in the search panel works well
         * (estimated price, warehouse logic, toggling, saving defaults)
         * ----------------------------------------------------------------
         */
        { trigger: ".o_purchase_order" },
        ...purchaseForm.createNewPO(),
        ...purchaseForm.selectVendor("Julia Agrolait"),
        ...purchaseForm.openCatalog(),
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

        // --- Check that suggestion feature does not appear on non draft POs ---
        ...productCatalog.goBackToOrder(),
        { trigger: ".o_purchase_order" },
        {
            content: "Confirm PO",
            trigger: 'button[name="button_confirm"]',
            run: "click",
        },
        ...purchaseForm.openCatalog(),
        { trigger: 'body:not(:has(div[name="search_panel_suggestion"]))' }, // Suggest should not show on non draft POs
        ...productCatalog.goBackToOrder(),
        {
            content: "Cancel PO",
            trigger: 'button[name="button_cancel"]',
            run: "click",
        },
        {
            content: "Reset to draft",
            trigger: 'button[name="button_draft"]',
            run: "click",
        },
        ...purchaseForm.openCatalog(),

        // --- Check suggestion uses PO warehouse (this WH only has 1 delivery) ---
        ...catalogSuggestion.toggleSuggest(true),
        {
            content: "Toggling Suggestion activates filter for products in PO or suggested",
            trigger: '.o_facet_value:contains("Suggested")', // Suggested
        },
        ...catalogSuggestion.setParameters({ basedOn: "Last 3 months", nbDays: 90, factor: 100 }),
        { trigger: "span[name='suggest_total']:visible:contains('$ 20.00')" },
        ...productCatalog.goBackToOrder(),
        ...purchaseForm.selectWarehouse("Base Warehouse: Receipts"),
        ...purchaseForm.openCatalog(),
        ...catalogSuggestion.setParameters({ basedOn: "Last 7 days", nbDays: 28, factor: 50 }),
        { trigger: "span[name='suggest_total']:visible:contains('$ 480.00')" }, // 12 units/week * 4 weeks * 20$/ unit * 50% = 480$

        // --- Check suggest parameters are saved on Add All ---
        ...catalogSuggestion.addAllSuggestions(),
        {
            content: "Wait a bit to make sure action is finished before navigating back",
            trigger: ".fa-trash",
            async run() {
                await new Promise((r) => setTimeout(r, 500));
            },
        },
        ...productCatalog.goBackToOrder(),
        ...purchaseForm.checkLineValues(0, { product: "test_product", quantity: "24.00" }),
        ...purchaseForm.createNewPO(),
        ...purchaseForm.selectVendor("Julia Agrolait"),
        ...purchaseForm.selectWarehouse("Base Warehouse: Receipts"),
        ...purchaseForm.openCatalog(),
        ...catalogSuggestion.assertParameters({ basedOn: "Last 7 days", nbDays: 28, factor: 50 }),
        /*
         * -----------------  PART 2 : Kanban Interactions -----------------
         * Checks the Suggest UI and the Kanban record interactions
         * (monthly demand, suggested_qty, forecasted + record ordering)
         * ------------------------------------------------------------------
         */
        ...catalogSuggestion.setParameters({ basedOn: "Last 7 days", nbDays: 28, factor: 50 }), // 1 order of 12
        { trigger: "span[name='suggest_total']:visible:contains('480')" },
        ...catalogSuggestion.assertCatalogRecord("test_product", { monthly: 52, suggest: 24 }),
        ...catalogSuggestion.checkKanbanRecordPosition("test_product", 0),

        ...catalogSuggestion.setParameters({ basedOn: "Last 30 days", factor: 10 }), // 2 orders of 12
        { trigger: "span[name='suggest_total']:visible:contains('60')" },
        ...catalogSuggestion.assertCatalogRecord("test_product", { monthly: 24, suggest: 3 }),

        ...catalogSuggestion.setParameters({ basedOn: "Last 3 months", factor: 500 }), // 2 orders of 12
        { trigger: "span[name='suggest_total']:visible:contains('740')" },
        ...catalogSuggestion.assertCatalogRecord("test_product", { monthly: 7.94, suggest: 37 }),

        // --- Check with Forecasted quantities
        ...catalogSuggestion.setParameters({ basedOn: "Forecasted", factor: 100 }),
        { trigger: "span[name='suggest_total']:visible:contains('2,000')" },
        ...catalogSuggestion.assertCatalogRecord("test_product", { forecast: 100, suggest: 100 }),

        ...catalogSuggestion.setParameters({ nbDays: 7 }),
        { trigger: "span[name='suggest_total']:visible:contains('$ 0.00')" }, // Move out of 100 in 20days, so no suggest for 7 days
        { trigger: ".o_view_nocontent_smiling_face" }, // Should suggest no products

        // --- Check with suggest OFF we come back to normal
        ...catalogSuggestion.toggleSuggest(false),
        ...catalogSuggestion.assertCatalogRecord("test_product", { forecast: 100, monthly: 24 }),
        ...catalogSuggestion.checkKanbanRecordPosition("Courage", 0),
        { trigger: "span[name='kanban_monthly_demand_qty']:visible:contains('24')" }, // Should come back to normal monthly demand
        /*
         * -------------------  PART 3 : KANBAN ACTIONS ---------------------
         * Checks suggest and kanban record interactions (purchase.order model)
         * (Add, remove and add all buttons)
         * ------------------------------------------------------------------
         */
        ...catalogSuggestion.toggleSuggest(true),
        ...catalogSuggestion.setParameters({ basedOn: "Last 7 days", nbDays: 28, factor: 50 }),
        {
            content: "Add suggestion from Record button",
            trigger: ".o_product_catalog_buttons .btn:has(.o_catalog_card_suggest_add)",
            run: "click",
        },
        ...productCatalog.waitForQuantity("test_product", 24),
        ...productCatalog.removeProduct("test_product"),
        {
            content: "Makes sure the update_order_line_info is processed on server before adding",
            trigger: ".btn:has(.o_catalog_card_suggest_add)",
            async run() {
                await new Promise((r) => setTimeout(r, 500));
            },
        },
        {
            content: "Add suggestion by clicking on the record",
            trigger: ".o_kanban_record",
            run: "click",
        },
        ...productCatalog.waitForQuantity("test_product", 24),
        {
            content: "Makes sure the update_order_line_info is processed on server before adding",
            trigger: ".fa-trash",
            async run() {
                await new Promise((r) => setTimeout(r, 500));
            },
        },
        { trigger: "div[name='kanban_purchase_suggest'] span:hidden" }, // If qty in PO == suggested_qty --> hide suggest string
        ...productCatalog.addProduct("test_product"), // Add product with "+" button
        ...productCatalog.waitForQuantity("test_product", 25),
        { trigger: "div[name='kanban_purchase_suggest'] span:visible" }, // If qty in PO != suggested_qty --> show suggest string
        {
            content: "Wait for a bit more then the 500 ms debouce on update quantity",
            trigger: ".fa-trash",
            async run() {
                await new Promise((r) => setTimeout(r, 700));
            },
        }, // Wait till its added on the server as well
        ...productCatalog.goBackToOrder(),
        ...purchaseForm.checkLineValues(0, { product: "test_product", quantity: "25.00" }),
        ...purchaseForm.openCatalog(),
        ...productCatalog.removeProduct("test_product"),
        {
            content: "Wait for a bit more then the 500 ms debouce on update quantity",
            trigger: ".o_product_catalog_buttons .btn:has(.o_catalog_card_suggest_add",
            async run() {
                await new Promise((r) => setTimeout(r, 700));
            },
        }, // Wait till its removed on the server as well
        // Should go back to displaying suggested qtys
        ...catalogSuggestion.assertCatalogRecord("test_product", { monthly: 52, suggest: 24 }),
        ...catalogSuggestion.checkKanbanRecordPosition("test_product", 0),
        /*
         * -------------------  PART 4 : KANBAN FILTERS ---------------------
         * Checks suggest and searchModel (filters) interactions
         * (Add / Remove with filters), category filters
         * ------------------------------------------------------------------
         */
        // ---- Check toggling suggest OFF with filters manually removed still works
        ...catalogSuggestion.removeSuggestFilter(),
        ...catalogSuggestion.toggleSuggest(false),
        { trigger: `.o_kanban_record:contains("Courage") button:has(.fa-plus,.fa-shopping-cart)` },
        ...catalogSuggestion.checkKanbanRecordPosition("Courage", 0), // == suggest is off

        // ---- Check Adding non suggested product works with suggest
        {
            content: "Add a non suggested product to order",
            trigger: "div.o_product_catalog_buttons i.fa-shopping-cart",
            run: "click",
        },
        ...catalogSuggestion.toggleSuggest(true),
        { trigger: '.o_facet_value:contains("Suggested")' }, // Should turn on filter Suggested or in the order
        ...catalogSuggestion.assertCatalogRecord("test_product", { monthly: 52, suggest: 24 }),
        ...catalogSuggestion.checkKanbanRecordPosition("Courage", 1), // Courage still shown because in order
        ...productCatalog.removeProduct("Courage"),

        // ---- Check Search Panel categories work with suggest
        ...productCatalog.selectSearchPanelCategory("Goods"),
        { trigger: "span[name='suggest_total']:visible:contains('$ 0.00')" }, // Should recompute estimated price
        ...productCatalog.selectSearchPanelCategory("Expenses"),
        { trigger: "span[name='suggest_total']:visible:contains('$ 480.00')" },
        ...catalogSuggestion.removeSuggestFilter(), // Shouldn't impact categories
        { trigger: "span[name='suggest_total']:visible:contains('$ 480.00')" },

        // ---- Finally done :)
        ...productCatalog.goBackToOrder(),
        {
            content: "Go back to the dashboard",
            trigger: ".o_menu_brand",
            run: "click",
        },
    ],
});
