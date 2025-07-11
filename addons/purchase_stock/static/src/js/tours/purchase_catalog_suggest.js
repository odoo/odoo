import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("purchase_catalog_suggest", {
    steps: () => [
        { trigger: ".o_purchase_order" },
        {
            content: "Create a New PO",
            trigger: ".o_list_button_add",
            run: "click",
        },
        {
            content: "Fill Vendor Field on PO",
            trigger: ".o_field_res_partner_many2one[name='partner_id'] input",
            tooltipPosition: "bottom",
            async run(actions) {
                const input = this.anchor.querySelector("input");
                await actions.edit("Julia Agrolait", input || this.anchor);
            },
        },
        {
            content: "Select Julia Agrolait as vendor",
            isActive: ["auto"],
            trigger: ".ui-menu-item > a:contains('Julia Agrolait')",
            run: "click",
        },
        {
            content: "Go to product catalog",
            trigger: 'button[name="action_add_from_catalog"]',
            run: "click",
        },
        { trigger: ".o_kanban_view.o_purchase_product_kanban_catalog_view" },
        {
            content: "Toggle the Suggest feature in search panel",
            trigger: 'button[name="toggle_suggest_catalog"]',
            run: "click",
        },
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
        {
            content: "Go back to the PO",
            trigger: "button.o-kanban-button-back",
            run: "click",
        },
        { trigger: ".o_form_view.o_purchase_order" },
        {
            content: "And back again to catalog",
            trigger: 'button[name="action_add_from_catalog"]',
            run: "click",
        },
        { trigger: ".o_kanban_view.o_purchase_product_kanban_catalog_view" },
        { trigger: "button[name='toggle_suggest_catalog'].fa-toggle-off" }, // Should still be off
        {
            content: "Toggle suggest ON",
            trigger: 'button[name="toggle_suggest_catalog"]',
            run: "click",
        },
        { trigger: "button[name='toggle_suggest_catalog'].fa-toggle-on" },
        {
            content: "Set reference period to last 3 month",
            trigger: ".o_TimePeriodSelectionField select",
            run: 'select "three_months"',
        },
        {
            content: "Changing number of days",
            trigger: "input.o_PurchaseSuggestInput:first-of-type",
            run: "edit 90",
        },
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
        {
            content: "Go back to the PO",
            trigger: "button.o-kanban-button-back",
            run: "click",
        },
        { trigger: ".o_form_view.o_purchase_order" },
        {
            content: "Fill Vendor Field on PO",
            trigger: ".o_field_many2one[name='picking_type_id'] input",
            tooltipPosition: "bottom",
            async run(actions) {
                const input = this.anchor.querySelector("input");
                await actions.edit("Base Warehouse: Receipts", input || this.anchor);
            },
        },
        {
            content: "Select BaseWarehouse as PO WH",
            isActive: ["auto"],
            trigger: ".ui-menu-item > a:contains('Base Warehouse: Receipts')",
            run: "click",
        },
        {
            content: "And back again to catalog",
            trigger: 'button[name="action_add_from_catalog"]',
            run: "click",
        },
        { trigger: ".o_kanban_view.o_purchase_product_kanban_catalog_view" },
        { trigger: "button[name='toggle_suggest_catalog'].fa-toggle-on" }, // Should still be ON
        {
            content: "Set reference period to last 3 month",
            trigger: ".o_TimePeriodSelectionField select",
            run: 'select "one_week"',
        },
        {
            content: "Changing number of days",
            trigger: "input.o_PurchaseSuggestInput:first-of-type",
            run: "edit 28",
        },
        {
            content: "Changing percent factor",
            trigger: "input.o_PurchaseSuggestInput:eq(1)",
            run: "edit 50",
        }, // Only saved when clicking ADD ALL (so now default based_on 1 month + replenish 100 days)
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
        },
        {
            content: "Go back to the PO",
            trigger: "button.o-kanban-button-back",
            run: "click",
        },
        { trigger: ".o_form_view.o_purchase_order" },
        {
            content: "Check product_frontend_test was added to PO",
            trigger: "div.o_field_product_label_section_and_note_cell span",
            run() {
                const first_prod = this.anchor.textContent.trim();
                if (!first_prod.includes("product_frontend_test")) {
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
        {
            content: "Fill Vendor Field on PO",
            trigger: ".o_field_res_partner_many2one[name='partner_id'] input",
            tooltipPosition: "bottom",
            async run(actions) {
                const input = this.anchor.querySelector("input");
                await actions.edit("Julia Agrolait", input || this.anchor);
            },
        },
        {
            content: "Select Julia Agrolait as vendor",
            isActive: ["auto"],
            trigger: ".ui-menu-item > a:contains('Julia Agrolait')",
            run: "click",
        },
        {
            content: "Go to product catalog",
            trigger: 'button[name="action_add_from_catalog"]',
            run: "click",
        },
        { trigger: ".o_kanban_view.o_purchase_product_kanban_catalog_view" },
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
            trigger: ".o_TimePeriodSelectionField select",
            run() {
                const value = this.anchor.value;
                if (value !== '"one_week"') {
                    throw new Error(`Expected based on to be saved to "one_week" got ${value}`);
                }
            },
        },
        {
            content: "Go back to the PO",
            trigger: "button.o-kanban-button-back",
            run: "click",
        },
        { trigger: ".o_form_view.o_purchase_order" },
        {
            content: "Create a New PO",
            trigger: ".o_form_button_create",
            run: "click",
        },
        {
            content: "Create a new Vendor",
            trigger: ".o_field_res_partner_many2one[name='partner_id'] input",
            tooltipPosition: "bottom",
            async run(actions) {
                const input = this.anchor.querySelector("input");
                await actions.edit("New Vendor", input || this.anchor);
            },
        },
        {
            content: "Select New Vendor as vendor",
            isActive: ["auto"],
            trigger: ".ui-menu-item > a:contains('New Vendor')",
            run: "click",
        },
        {
            content: "Go to product catalog",
            trigger: 'button[name="action_add_from_catalog"]',
            run: "click",
        },
        { trigger: ".o_kanban_view.o_purchase_product_kanban_catalog_view" },
        {
            content: "Open the panel",
            trigger: ".o_search_panel_sidebar button",
            run: "click",
        },
        { trigger: ".o_search_panel" },
        {
            content: "Check the suggest wizard is gone",
            trigger: ".o_search_panel",
            run() {
                if (document.querySelector('[name="toggle_suggest_catalog"]')) {
                    throw new Error("Suggest wizard is still visible!");
                }
            },
        },
        {
            content: "Go back to the dashboard",
            trigger: ".o_menu_brand",
            run: "click",
        },
    ],
});
