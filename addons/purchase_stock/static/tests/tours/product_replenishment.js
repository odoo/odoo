import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_product_replenishment", {
    steps: () => [
        // Show Route column
        {
            content: "Open line fields list",
            trigger: ".o_optional_columns_dropdown_toggle",
            run: "click",
        },
        {
            content: "Show route column",
            trigger: '.o-dropdown-item input[name="route_id"]',
            run: async ({ anchor }) => {
                // We need this condition because `route_id` field is hidden by
                // default except if `purchase_mrp` is installed.
                if (!anchor.checked) {
                    anchor.click();
                }
            },
        },
        {
            content: "Close line fields list",
            trigger: ".o_optional_columns_dropdown_toggle",
            run: "click",
        },
        // Create reordering rule for product 'Book Shelf'
        {
            content: "Click New Button",
            trigger: 'button:contains("New")',
            run: "click",
        },
        {
            content: "Select Buy Route",
            trigger: '.o_selected_row .o_list_many2one[name="route_id"] input',
            run: "edit Buy",
        },
        {
            content: "Valid Route",
            trigger: '.ui-menu-item-wrapper:contains("Buy")',
            run: "click",
        },
        {
            content: "Select Product",
            trigger: '.o_selected_row .o_list_many2one[name="product_id"] input',
            run: "edit Book Shelf",
        },
        {
            content: "Valid Product",
            trigger: '.ui-menu-item-wrapper:contains("Book Shelf")',
            run: "click",
        },
        {
            content: "Save the Rule",
            trigger: 'button:contains("Save")',
            run: "click",
        },
        {
            content: "Wait for the reordering rule to be added",
            trigger: '.o_data_row td:contains("Book Shelf")',
        },
    ],
});

registry.category("web_tour.tours").add("test_replenishment_supplier_multicompany_access", {
    steps: () => [
        {
            content: "Open optional columns",
            trigger: ".o_optional_columns_dropdown_toggle",
            run: "click",
        },
        {
            content: "Show Vendor column",
            trigger: '.o-dropdown-item input[name="supplier_id"]',
            run: ({ anchor }) => {
                if (!anchor.checked) {
                    anchor.click();
                }
            },
        },
        {
            content: "Show route column",
            trigger: '.o-dropdown-item input[name="route_id"]',
            run: ({ anchor }) => {
                if (!anchor.checked) {
                    anchor.click();
                }
            },
        },
        {
            content: "Close optional columns",
            trigger: ".o_optional_columns_dropdown_toggle",
            run: "click",
        },
        {
            content: "Click New Button",
            trigger: 'button:contains("New")',
            run: "click",
        },
        {
            content: "Select Product A",
            trigger: '.o_selected_row .o_list_many2one[name="product_id"] input',
            run: "edit Product A",
        },
        {
            content: "Confirm Product A selection",
            trigger: '.ui-menu-item-wrapper:contains("Product A")',
            run: "click",
        },
        {
            content: "Select Buy Route",
            trigger: '.o_selected_row .o_list_many2one[name="route_id"] input',
            run: "edit Buy",
        },
        {
            content: "Confirm Buy route selection",
            trigger: '.ui-menu-item-wrapper:contains("Buy")',
            run: "click",
        },
        {
            content: "Edit the vendor field",
            trigger: '.o_selected_row .o_list_many2one[name="supplier_id"] input',
            run: "edit Partner A",
        },
        {
            content: "Select the valid vendor",
            trigger: '.ui-menu-item-wrapper:contains("Partner A")',
            run: "click",
        },
        {
            content: "Save the edited row",
            trigger: 'button:contains("Save")',
            run: "click",
        },
        {
            content: "Verify no access error dialog is shown",
            trigger: ".o_web_client:not(:has(.o_error_dialog))",
        },
        {
            content: "Verify vendor was saved correctly",
            trigger:
                '.o_data_row:contains("Product A") .o_data_cell[name="supplier_id"]:contains("Partner A")',
        },
    ],
});

registry.category("web_tour.tours").add("test_forecast_po_line_multi_date", {
    steps: () => [
        {
            trigger: ".o_kanban_record:contains('Storable Product')",
            run: "click",
        },
        {
            trigger: "button[name=action_product_tmpl_forecast_report]",
            run: "click",
        },
        {
            trigger: ".o_forecasted_details_table",
            run: () => {
                // Assert two separate incoming rows (not merged)
                const links = document.querySelectorAll(
                    ".o_forecasted_details_table td a.fw-bold"
                );
                if (links.length !== 2) {
                    throw new Error(
                        `Expected 2 separate incoming forecast lines but found ${links.length}. ` +
                        `PO lines with different date_planned are incorrectly merged.`
                    );
                }
            },
        },
    ],
});
