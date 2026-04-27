/** @odoo-module */

import * as helper from "./tour_helper_stock_barcode";
import { registry } from "@web/core/registry";
import { stepUtils } from "./tour_step_utils";

registry.category("web_tour.tours").add("test_inventory_adjustment", {
    steps: () => [
        {
            trigger: ".o_button_inventory",
            run: "click",
        },

        {
            trigger: ".o_scan_message.o_scan_product",
            run: function () {
                helper.assertScanMessage("scan_product");
                helper.assertValidateVisible(true);
                helper.assertValidateIsHighlighted(false);
                helper.assertValidateEnabled(false);
            },
        },

        { trigger: ".o_barcode_client_action", run: "scan product1" },
        {
            trigger: ".o_barcode_line",
            run: function () {
                // Checks the product code and name are on separate lines.
                const line = helper.getLine({ barcode: "product1" });
                helper.assert(
                    line.querySelectorAll(
                        ".o_barcode_line_title > .o_product_ref + .o_product_label"
                    ).length,
                    1
                );
            },
        },

        { trigger: ".o_barcode_client_action", run: "scan product1" },
        { trigger: ".o_barcode_line .qty-done:contains(2)" },

        { trigger: ".o_edit", run: "click" },

        {
            trigger: '.o_field_widget[name="inventory_quantity"]',
            run: function () {
                helper.assertFormQuantity("2");
            },
        },

        {
            trigger: ".o_save",
            run: "click",
        },

        {
            trigger: ".o_barcode_line",
            run: function () {
                // Checks the product code and name are on separate lines.
                const line = helper.getLine({ barcode: "product1" });
                helper.assert(
                    line.querySelectorAll(
                        ".o_barcode_line_title > .o_product_ref + .o_product_label"
                    ).length,
                    1
                );
            },
        },

        {
            trigger: ".o_add_line",
            run: "click",
        },

        {
            trigger: ".o_field_widget[name=product_id] input",
            run: "edit product2",
        },

        {
            trigger: ".ui-menu-item > a:contains('product2')",
            run: "click",
        },

        {
            trigger: ".o_field_widget[name=inventory_quantity] input",
            run: "edit 2",
        },

        {
            trigger: ".o_save",
            run: "click",
        },
        {
            trigger: ".o_scan_message.o_scan_product",
        },
        {
            trigger: ".o_barcode_line",
            run: "scan OBTVALI",
        },

        {
            trigger: ".o_stock_barcode_main_menu",
            run: "click",
        },

        {
            trigger: ".o_notification_bar.bg-success",
            run: function () {
                helper.assertErrorMessage("The inventory count has been updated");
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_inventory_adjustment_dont_update_location", {
    steps: () => [
        {
            trigger: ".o_button_inventory",
            run: "click",
        },
        {
            trigger: ".o_barcode_client_action",
            run: function () {
                helper.assertLinesCount(2);
                const [line1, line2] = helper.getLines({ barcode: "product1" });
                helper.assertLineQty(line1, "0/5");
                helper.assertLineQty(line2, "0/5");
                helper.assertLineSourceLocation(line1, "WH/Stock");
                helper.assertLineSourceLocation(line2, "WH/Stock/Section 2");
            },
        },
        // Scan WH/Stock/Section 1.
        {
            trigger: ".o_barcode_client_action",
            run: "scan LOC-01-01-00",
        },
        { trigger: ".o_barcode_location_line[data-location='WH/Stock'].text-muted" },
        {
            trigger: ".o_barcode_location_group:first-child .o_barcode_line",
            run: "click",
        },
        {
            trigger: ".o_barcode_line.o_selected button.o_add_quantity",
            run: "click",
        },
        {
            trigger: "button.o_remove_unit:enabled",
            run: function () {
                helper.assertLinesCount(2);
                const selectedLine = helper.getLine({ selected: true });
                helper.assertLineQty(selectedLine, "1/5");
                helper.assertLineSourceLocation(selectedLine, "WH/Stock");
            },
        },
        // Scans product1 -> A new line for this product should be created in Section 1.
        {
            trigger: ".o_barcode_client_action",
            run: "scan product1",
        },
        {
            trigger:
                '.o_barcode_location_line[data-location="WH/Stock/Section 1"] + .o_barcode_line',
            run: function () {
                helper.assertLinesCount(3);
                const selectedLine = helper.getLine({ selected: true });
                helper.assertLineQty(selectedLine, "1");
                helper.assertLineSourceLocation(selectedLine, "WH/Stock/Section 1");
            },
        },
        ...stepUtils.validateBarcodeOperation(".o_apply_page.btn-primary"),
    ],
});

registry.category("web_tour.tours").add("test_inventory_adjustment_multi_company", {
    steps: () => [
        // Open the company switcher.
        {
            trigger: ".o_switch_company_menu > button",
            run: "click",
        },
        // Ensure the first company is selected and open the Barcode App, then the Inventory Adjustment.
        {
            trigger: ".o_switch_company_menu .oe_topbar_name:contains('Comp A')",
        },
        {
            trigger: "[data-menu-xmlid='stock_barcode.stock_barcode_menu'] > .o_app_icon",
            run: "click",
        },
        {
            trigger: "button.o_button_inventory",
            run: "click",
        },
        // Scan product1 and product_no_company, they should be added in the inventory adj.
        {
            trigger: ".o_barcode_client_action",
            run: "scan product1",
        },
        {
            trigger: ".o_barcode_line[data-barcode='product1']",
            run: "scan product_no_company",
        },
        // Try to scan product2 who belongs to the second company -> Should not be found.
        {
            trigger: ".o_barcode_line[data-barcode='product_no_company']",
            run: "scan product2",
        },
        {
            trigger: ".o_notification_bar.bg-danger",
        },
        {
            trigger: ".o_notification button.o_notification_close",
            run: "click",
        },
        {
            trigger: ".o_barcode_client_action",
            run: function () {
                helper.assertLinesCount(2);
            },
        },
        // Validate the Inventory Adjustment.
        {
            trigger: ".o_apply_page.btn-primary",
            run: "click",
        },

        // Go back on the App Switcher and change the company.
        {
            trigger: ".o_stock_barcode_main_menu a.oi-apps",
            run: "click",
        },
        {
            trigger: ".o_switch_company_menu > button",
            run: "click",
        },
        {
            trigger: ".o-dropdown--menu .company_label:contains('Comp B')",
            run: "click",
        },
        // Open again the Barcode App then the Inventory Adjustment.
        {
            trigger: ".o_switch_company_menu .oe_topbar_name:contains('Comp B')",
        },
        {
            trigger: "[data-menu-xmlid='stock_barcode.stock_barcode_menu'] > .o_app_icon",
            run: "click",
        },
        {
            trigger: "button.o_button_inventory",
            run: "click",
        },
        // Scan product2 and product_no_company, they should be added in the inventory adj.
        {
            trigger: ".o_barcode_client_action",
            run: "scan product2",
        },
        {
            trigger: ".o_barcode_line[data-barcode='product2']",
            run: "scan product_no_company",
        },
        // Try to scan product1 who belongs to the first company -> Should not be found.
        {
            trigger: ".o_barcode_line[data-barcode='product_no_company']",
            run: "scan product1",
        },
        {
            trigger: ".o_notification_bar.bg-danger",
        },
        {
            trigger: ".o_notification button.o_notification_close",
            run: "click",
        },
        {
            trigger: ".o_barcode_client_action",
            run: function () {
                helper.assertLinesCount(2);
            },
        },
        // Validate the Inventory Adjustment.
        {
            trigger: ".o_barcode_line",
            run: "scan OBTVALI",
        },
        {
            trigger: ".o_notification_bar.bg-success",
        },
        {
            trigger: ".o_stock_barcode_main_menu",
            run: function () {
                helper.assertErrorMessage("The inventory count has been updated");
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_inventory_adjustment_multi_location", {
    steps: () => [
        {
            trigger: ".o_button_inventory",
            run: "click",
        },
        {
            trigger: ".o_barcode_client_action",
            run: "scan LOC-01-00-00",
        },
        {
            trigger: '.o_scan_message:contains("WH/Stock")',
            run: "click",
        },
        {
            trigger: ".o_barcode_client_action",
            run: "scan product1",
        },
        ...stepUtils.inputManuallyBarcode("product1"),
        {
            trigger: ".o_barcode_client_action",
            run: "scan product2",
        },
        {
            trigger: ".o_barcode_client_action",
            run: "scan LOC-01-01-00",
        },
        {
            trigger: '.o_scan_message:contains("WH/Stock/Section 1")',
            run: "click",
        },
        {
            trigger: ".o_barcode_client_action",
            run: "scan product2",
        },
        {
            trigger: ".o_barcode_client_action",
            run: "scan LOC-01-02-00",
        },
        {
            trigger: '.o_scan_message:contains("WH/Stock/Section 2")',
            run: "click",
        },
        {
            trigger: ".o_barcode_client_action",
            run: "scan product1",
        },
        {
            trigger: ".o_barcode_client_action",
            run: "scan OBTVALI",
        },
        {
            trigger: ".o_stock_barcode_main_menu",
            run: function () {
                helper.assertErrorMessage("The inventory count has been updated");
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_inventory_adjustment_tracked_product", {
    steps: () => [
        {
            trigger: ".o_button_inventory",
            run: "click",
        },
        {
            trigger: ".o_barcode_client_action",
            run: "scan productlot1",
        },
        {
            trigger: '.o_barcode_line:contains("productlot1")',
            run: "scan lot1",
        },
        {
            trigger: ".o_barcode_client_action",
            run: "scan lot1",
        },
        {
            trigger: ".o_barcode_line.o_selected .qty-done:contains(2)",
            run: "scan productserial1",
        },
        {
            trigger: '.o_barcode_line:contains("productserial1")',
            run: "scan serial1",
        },
        {
            trigger: ".o_barcode_client_action",
            run: "scan serial1",
        },
        {
            trigger: ".o_notification_bar.bg-danger",
            run: function () {
                // Check that other lines is correct
                let line = helper.getLine({ barcode: "productserial1" });
                helper.assertLineQty(line, "1");
                helper.assert(line.querySelector(".o_line_lot_name").innerText.trim(), "serial1");
                line = helper.getLine({ barcode: "productlot1" });
                helper.assertLineQty(line, "2");
                helper.assert(line.querySelector(".o_line_lot_name").innerText.trim(), "lot1");
                helper.assertErrorMessage("The scanned serial number serial1 is already used.");
            },
        },
        {
            trigger: ".o_barcode_client_action",
            run: "scan serial2",
        },
        {
            trigger: '.o_barcode_line:contains("serial2")',
            run: "scan productlot1",
        },
        {
            trigger: '.o_barcode_line[data-barcode="productlot1"].o_selected',
            run: "scan lot1",
        },
        {
            trigger: ".o_barcode_line.o_selected .qty-done:contains(3)",
            run: "scan productserial1",
        },
        {
            trigger: '.o_barcode_line[data-barcode="productserial1"].o_selected',
            run: "scan serial3",
        },
        {
            trigger:
                '[data-barcode="productserial1"] .o_sublines .o_barcode_line:contains("serial3")',
            run: function () {
                helper.assertLinesCount(2);
                helper.assertSublinesCount(3);
            },
        },
        // Add a new line (it also triggers a save.)
        {
            trigger: ".o_add_line",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name=product_id] input",
            run: "edit productserial1",
        },
        {
            trigger: ".ui-menu-item > a:contains('productserial1')",
            run: "click",
        },
        {
            trigger: ".o_save",
            run: "click",
        },
        // Scan tracked by lots product, then scan new lots.
        {
            trigger: ".o_sublines .o_barcode_line:nth-child(4)",
            run: function () {
                helper.assertLinesCount(2);
                helper.assertSublinesCount(4);
            },
        },
        {
            trigger: ".o_barcode_client_action",
            run: "scan productlot1",
        },
        {
            trigger: '.o_barcode_line[data-barcode="productlot1"].o_selected',
            run: "scan lot2",
        },
        {
            trigger: '.o_barcode_line .o_barcode_line.o_selected:contains("lot2")',
            run: "scan lot3",
        },
        // Must have 6 lines in two groups: lot1, lot2, lot3 and serial1, serial2, serial3.
        // Grouped lines for `productlot1` should be unfolded.
        {
            trigger:
                '.o_barcode_line:contains("productlot1") .o_sublines>.o_barcode_line.o_selected:contains("lot3")',
            run: function () {
                helper.assertLinesCount(2);
                helper.assertSublinesCount(3);
            },
        },
        {
            trigger: ".o_barcode_client_action",
            run: "scan OBTVALI",
        },
        // Confirm modal (because one of the line tracked by serial number has no SN.)
        {
            trigger: ".modal-header",
            run: "click",
        },
        {
            trigger: "button[name=action_confirm]:enabled",
            run: "click",
        },
        {
            trigger: ".o_notification_bar.bg-success",
            run: "click",
        },
        {
            trigger: ".o_stock_barcode_main_menu",
            run: function () {
                helper.assertErrorMessage("The inventory count has been updated");
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_inventory_adjustment_tracked_product_multilocation", {
    steps: () => [
        {
            trigger: ".o_button_inventory",
            run: "click",
        },
        {
            trigger: ".o_barcode_line",
            run: function () {
                helper.assertLinesCount(2);
                helper.assertLineSourceLocation(0, "WH/Stock/Section 1");
                helper.assertLineQty(0, "3/3");
                helper.assertLineSourceLocation(1, "WH/Stock/Section 2");
                helper.assertLineQty(1, "0/5");
            },
        },
        // Scans Section 1 then scans productlot1 -> It should update the first productlot1's line.
        {
            trigger: ".o_barcode_line",
            run: "scan LOC-01-01-00",
        },
        {
            trigger: ".o_barcode_location_line[data-location='WH/Stock/Section 1'].text-bg-800",
            run: "scan lot1",
        },
        {
            trigger: ".o_barcode_location_group:first-child .o_barcode_line.o_selected",
            run: function () {
                helper.assertLineSourceLocation(0, "WH/Stock/Section 1");
                helper.assertLineQty(0, "4/3");
                helper.assertLineSourceLocation(1, "WH/Stock/Section 2");
                helper.assertLineQty(1, "0/5");
            },
        },
        // Scans productserial1 -> As we are in Section 1, it should get sn1, sn2 and sn3.
        {
            trigger: ".o_barcode_client_action",
            run: "scan productserial1",
        },
        {
            trigger: ".o_barcode_line:nth-child(3).o_selected",
            run: function () {
                helper.assertLinesCount(3);
                const serialLine = helper.getLine({ barcode: "productserial1" });
                helper.assertLineSourceLocation(serialLine, "WH/Stock/Section 1");
                helper.assertLineQty(1, "?/3");
                helper.assertSublinesCount(3);
                const [subline1, subline2, subline3] = helper.getSublines();
                helper.assertLineQty(subline1, "?/1");
                helper.assertLineQty(subline2, "?/1");
                helper.assertLineQty(subline3, "?/1");
                helper.assert(subline1.querySelector(".o_line_lot_name").innerText, "sn1");
                helper.assert(subline2.querySelector(".o_line_lot_name").innerText, "sn2");
                helper.assert(subline3.querySelector(".o_line_lot_name").innerText, "sn3");
            },
        },
        // Hides sublines.
        {
            trigger: ".o_barcode_line.o_selected .btn.o_toggle_sublines .fa-angle-up",
            run: "click",
        },
        // Scans Section 2 then scans productlot1 -> It should update the second productlot1's line.
        {
            trigger: ".o_barcode_line",
            run: "scan LOC-01-02-00",
        },
        {
            trigger: ".o_barcode_location_line[data-location='WH/Stock/Section 2'].text-bg-800",
            run: "scan lot1",
        },
        {
            trigger: ".o_barcode_location_group:nth-child(2) .o_barcode_line.o_selected",
            run: function () {
                const [lotLine1, lotLine2] = helper.getLines({ barcode: "productlot1" });
                helper.assertLineSourceLocation(lotLine1, "WH/Stock/Section 1");
                helper.assertLineQty(0, "4/3");
                helper.assertLineSourceLocation(lotLine2, "WH/Stock/Section 2");
                helper.assertLineQty(2, "1/5");
            },
        },
        // Scans productserial1 -> No existing quant in Section 2 for this product so creates a new line.
        {
            trigger: ".o_barcode_client_action",
            run: "scan productserial1",
        },
        {
            trigger: ".o_barcode_line:nth-child(3).o_selected",
            run: function () {
                helper.assertLinesCount(4);
                const [serialLine1, serialLine2] = helper.getLines({ barcode: "productserial1" });
                helper.assertLineSourceLocation(serialLine1, "WH/Stock/Section 1");
                helper.assertLineQty(serialLine1, "?/3");
                helper.assertLineSourceLocation(serialLine2, "WH/Stock/Section 2");
                helper.assertLineQty(serialLine2, "0");
            },
        },
        ...stepUtils.validateBarcodeOperation(),
        {
            trigger: ".o_stock_barcode_main_menu",
            run: function () {
                helper.assertErrorMessage("The inventory count has been updated");
            },
        },
    ],
});

registry
    .category("web_tour.tours")
    .add("test_inventory_adjustment_tracked_product_permissive_quants", {
        steps: () => [
            {
                trigger: ".o_button_inventory",
                run: "click",
            },
            {
                trigger: ".o_barcode_client_action",
                run: function () {
                    helper.assertLinesCount(0);
                },
            },

            // Scan a product tracked by lot that has a quant without lot_id, then scan a product's lot.
            {
                trigger: ".o_barcode_client_action",
                run: "scan productlot1",
            },
            {
                trigger: '.o_barcode_line:contains("productlot1")',
                run: function () {
                    helper.assertLinesCount(1);
                    helper.assertSublinesCount(0);
                    const line = helper.getLine();
                    helper.assertLineQty(line, "?/5");
                    helper.assertLinesTrackingNumbers([line], [""]);
                },
            },
            {
                trigger: ".o_barcode_client_action",
                run: "scan lot1",
            },
            {
                trigger: ".o_barcode_client_action",
                run: "scan lot1",
            },
            // Must have 2 lines in one group: one without lot and one with lot1.
            // Grouped lines for `productlot1` should be unfolded.
            {
                trigger:
                    '.o_sublines .o_barcode_line.o_selected:contains("lot1") .qty-done:contains(2)',
                run: function () {
                    helper.assertLinesCount(1);
                    helper.assertSublinesCount(2);
                    const [subline1, subline2] = helper.getSublines();
                    helper.assertLineQty(subline1, "?/5");
                    helper.assertLineQty(subline2, "2");
                },
            },

            { trigger: ".o_sublines .o_barcode_line:first-child", run: "click" },
            {
                trigger: ".o_sublines .o_barcode_line:first-child.o_selected button.o_count_zero",
                run: "click",
            },
            ...stepUtils.validateBarcodeOperation(
                ".o_sublines .o_barcode_line:first-child button.o_unset"
            ),

            {
                trigger: ".o_stock_barcode_main_menu",
                run: function () {
                    helper.assertErrorMessage("The inventory count has been updated");
                },
            },
        ],
    });

registry.category("web_tour.tours").add("test_inventory_create_quant", {
    steps: () => [
        {
            trigger: ".o_button_inventory",
            run: "click",
        },
        {
            trigger: ".o_barcode_client_action",
            run: function () {
                helper.assertLinesCount(0);
            },
        },

        // Scans product 1: must have 1 quantity and buttons +1/-1 must be visible.
        {
            trigger: ".o_barcode_client_action",
            run: "scan product1",
        },
        {
            trigger: ".o_barcode_client_action .o_barcode_line",
            run: function () {
                helper.assertLinesCount(1);
                const line = helper.getLine({ barcode: "product1" });
                helper.assertLineIsHighlighted(line, true);
                helper.assertLineQty(line, "1");
                helper.assertButtonIsVisible(line, "add_quantity");
                helper.assertButtonIsVisible(line, "remove_unit");
            },
        },

        // Edits the line to set the counted quantity to zero.
        {
            trigger: ".o_edit",
            run: "click",
        },
        {
            trigger: '.o_field_widget[name="product_id"]',
            run: function () {
                helper.assertFormQuantity("1");
            },
        },
        {
            trigger: ".o_field_widget[name=inventory_quantity] input",
            run: "edit 0",
        },
        {
            trigger: ".o_save",
            run: "click",
        },
        {
            trigger: ".o_barcode_client_action .o_barcode_line",
            run: function () {
                helper.assertLinesCount(1);
                const line = helper.getLine({ barcode: "product1" });
                helper.assertLineQty(line, "0");
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_inventory_dialog_not_counted_serial_numbers", {
    steps: () => [
        { trigger: ".o_button_inventory", run: "click" },
        {
            trigger: ".o_barcode_client_action",
            run: () => {
                helper.assertLinesCount(3);
                helper.assertLineProduct(0, "productserial1");
                helper.assertLineQty(0, "?/3");
                helper.assertLineSourceLocation(0, "WH/Stock/Section 1");
                helper.assertLineProduct(1, "productserial1");
                helper.assertLineQty(1, "?/3");
                helper.assertLineSourceLocation(1, "WH/Stock/Section 2");
                helper.assertLineProduct(2, "productserial2");
                helper.assertLineQty(2, "?/3");
                helper.assertLineSourceLocation(2, "WH/Stock/Section 2");
            },
        },
        // Scan 1 SN for productserial1 in Section 1 and apply => Dialog should be displayed.
        { trigger: ".o_scan_message.o_scan_src", run: "scan LOC-01-01-00" },
        { trigger: ".o_scan_message.o_scan_product_or_src", run: "scan productserial1" },
        { trigger: ".o_barcode_line.o_selected", run: "scan sn1" },
        { trigger: ".o_apply_page:enabled", run: "click" },
        { trigger: ".o_stock_barcode_apply_quant_dialog" },
        // Apply only counted quant and reopen the Inv. Adjust. => other Section 1 quants are still here.
        { trigger: ".o_dialog button.o_apply", run: "click" },
        { trigger: ".o_button_inventory", run: "click" },
        {
            trigger: ".o_barcode_client_action",
            run: () => {
                helper.assertLinesCount(3);
                helper.assertLineProduct(0, "productserial1");
                helper.assertLineQty(0, "?/2");
                helper.assertLineSourceLocation(0, "WH/Stock/Section 1");
                helper.assertLineProduct(1, "productserial1");
                helper.assertLineQty(1, "?/3");
                helper.assertLineSourceLocation(1, "WH/Stock/Section 2");
                helper.assertLineProduct(2, "productserial2");
                helper.assertLineQty(2, "?/3");
                helper.assertLineSourceLocation(2, "WH/Stock/Section 2");
            },
        },
        // Scan a SN for productserial1 in Section 1 and apply => Apply also not counted SN.
        { trigger: ".o_scan_message.o_scan_src", run: "scan LOC-01-01-00" },
        { trigger: ".o_scan_message.o_scan_product_or_src", run: "scan productserial1" },
        { trigger: ".o_barcode_line.o_selected", run: "scan sn2" },
        { trigger: ".o_barcode_line.o_selected.o_line_completed" },
        { trigger: ".o_apply_page:enabled", run: "click" },
        { trigger: ".o_stock_barcode_apply_quant_dialog" },
        { trigger: ".o_dialog button.o_apply_all", run: "click" },
        // Reopen the Inventory Adjustment.
        { trigger: ".o_button_inventory", run: "click" },
        {
            trigger: ".o_barcode_client_action",
            run: () => {
                helper.assertLinesCount(2);
                helper.assertLineProduct(0, "productserial1");
                helper.assertLineQty(0, "?/3");
                helper.assertLineSourceLocation(0, "WH/Stock/Section 2");
                helper.assertLineProduct(1, "productserial2");
                helper.assertLineQty(1, "?/3");
                helper.assertLineSourceLocation(1, "WH/Stock/Section 2");
            },
        },
        // Scan all SN for productserial1 in Section 2 and apply => Dialog should
        // not be displayed (remaining SN in this location is for another product.)
        { trigger: ".o_scan_message.o_scan_src", run: "scan LOC-01-02-00" },
        { trigger: ".o_scan_message.o_scan_product_or_src", run: "scan productserial1" },
        { trigger: ".o_barcode_line.o_selected", run: "scan sn4,sn5,sn6" },
        { trigger: ".o_barcode_line.o_selected.o_line_completed" },
        { trigger: ".o_apply_page", run: "click" },
        // Reopen the Inventory Adjustment and scan remaining SN for productserial2.
        { trigger: ".o_button_inventory", run: "click" },
        {
            trigger: ".o_barcode_client_action",
            run: () => {
                helper.assertLinesCount(1);
                helper.assertLineProduct(0, "productserial2");
                helper.assertLineQty(0, "?/3");
                helper.assertLineSourceLocation(0, "WH/Stock/Section 2");
            },
        },
        { trigger: ".o_scan_message.o_scan_src", run: "scan LOC-01-02-00" },
        { trigger: ".o_scan_message.o_scan_product_or_src", run: "scan productserial2" },
        { trigger: ".o_barcode_line.o_selected", run: "scan sn1,sn2,sn3" },
        // Apply => No dialog because all SN are counted.
        ...stepUtils.validateBarcodeOperation(".o_barcode_line.o_selected.o_line_completed"),
        { trigger: ".o_stock_barcode_main_menu" },
    ],
});

registry.category("web_tour.tours").add("test_inventory_image_visible_for_quant", {
    steps: () => [
        { trigger: "button.o_button_inventory", run: "click" },
        { trigger: ".o_barcode_line:first-child button.o_edit", run: "click" },
        {
            trigger: ".o_form_view",
            run: function () {
                const imgEl = document.querySelector("div[name=image_1920] img");
                helper.assert(Boolean(imgEl), true, "Product image should be visible");
            },
        },
        { trigger: "button.o_discard", run: "click" },
        { trigger: ".o_barcode_line:nth-child(2) button.o_edit", run: "click" },
        {
            trigger: ".o_form_view",
            run: function () {
                const imgEl = document.querySelector("div[name=image_1920] img");
                helper.assert(Boolean(imgEl), false, "Product has no image set");
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_inventory_nomenclature", {
    steps: () => [
        {
            trigger: ".o_button_inventory",
            run: "click",
        },
        {
            trigger: ".o_barcode_client_action",
            run: function () {
                helper.assertScanMessage("scan_product");
            },
        },
        {
            trigger: ".o_barcode_client_action",
            run: "scan 2145631123457", // 12.345 kg
        },
        {
            trigger: '.o_product_label:contains("product_weight")',
            run: "click",
        },
        ...stepUtils.validateBarcodeOperation(),
        {
            trigger: ".o_stock_barcode_main_menu",
            run: function () {
                helper.assertErrorMessage("The inventory count has been updated");
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_inventory_package", {
    steps: () => [
        {
            trigger: ".o_button_inventory",
            run: "click",
        },
        {
            trigger: ".o_barcode_client_action",
            run: "scan PACK001",
        },
        {
            trigger: '.o_barcode_line:contains("product2") .o_edit',
            run: "click",
        },
        {
            trigger: '[name="inventory_quantity"] input',
            run: "edit 21",
        },
        {
            trigger: ".o_save",
            run: "click",
        },
        {
            trigger: ".o_apply_page",
            run: "click",
        },

        {
            trigger: ".o_notification_bar.bg-success",
            run: function () {
                helper.assertErrorMessage("The inventory count has been updated");
            },
        },

        {
            trigger: ".o_stock_barcode_main_menu",
        },
    ],
});

registry.category("web_tour.tours").add("test_inventory_packaging", {
    steps: () => [
        {
            trigger: ".o_button_inventory",
            run: "click",
        },
        // Scans a packaging when there is no existing quant for its product.
        {
            trigger: ".o_barcode_client_action",
            run: "scan pack007",
        },
        {
            trigger: ".o_barcode_line",
            run: function () {
                const $line = helper.getLine({ barcode: "product1" });
                helper.assertLineQty($line, "15");
            },
        },
        {
            trigger: ".o_apply_page",
            run: "click",
        },
        {
            trigger: ".o_notification_bar.bg-success",
            run: "click",
        },
        {
            trigger: ".o_button_inventory",
            run: "click",
        },
        // Scans a packaging when a quant for its product exists.
        {
            trigger: ".o_barcode_client_action",
            run: "scan pack007",
        },
        // Verifies it takes the packaging's quantity.
        {
            trigger: ".o_barcode_line .qty-done:contains(15)",
        },
        {
            trigger: ".o_apply_page",
            run: "click",
        },
        {
            trigger: ".o_notification_bar.bg-success",
        },
    ],
});

registry.category("web_tour.tours").add("test_inventory_serial_product_packaging", {
    steps: () => [
        { trigger: ".o_button_inventory", run: "click" },
        { trigger: ".o_barcode_client_action", run: "scan PCK3" },
        {
            trigger: ".o_barcode_line.o_highlight",
            run: function () {
                helper.assertLinesCount(1);
                helper.assertLineProduct(0, "productserial1");
                helper.assertLineQty(0, "3");
                helper.assertSublinesCount(3);
                const [subline1, subline2, subline3] = helper.getSublines();
                helper.assertLineQty(subline1, "1");
                helper.assertLineQty(subline2, "1");
                helper.assertLineQty(subline3, "1");
            },
        },
        { trigger: ".o_barcode_client_action", run: "scan sn1" },
        { trigger: ".o_barcode_client_action", run: "scan sn2" },
        { trigger: ".o_barcode_client_action", run: "scan sn3" },
        {
            trigger: '.o_barcode_client_action:contains("sn3")',
            run: function () {
                helper.assertSublinesCount(3);
                const sublines = helper.getSublines();
                helper.assertLinesTrackingNumbers(sublines, ["sn3", "sn2", "sn1"]);
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_inventory_packaging_button", {
    steps: () => [
        {
            trigger: ".o_button_inventory",
            run: "click",
        },
        {
            trigger: "button.o_add_line",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='product_id'] .o_input",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='product_id'] .o_input",
            run: "edit Lovely Product",
        },
        {
            trigger: ".dropdown-item:contains('Lovely Product')",
            run: "click",
        },
        {
            content: "check that the packaging buttons were updated.",
            trigger: ".o_digipad_digit_buttons button:contains(LP x15)",
        },
        {
            content: "Add 15 units via the button.",
            trigger: ".o_digipad_digit_buttons button:contains(LP x15)",
            run: "click",
        },
        {
            trigger: ".o_save",
            run: "click",
        },
        {
            content: "Check that the inventory adjustment was registered.",
            trigger: ".o_barcode_lines .qty-done:contains(15)",
        },
    ],
});

registry.category("web_tour.tours").add("test_inventory_owner_scan_package", {
    steps: () => [
        {
            trigger: ".o_button_inventory",
            run: "click",
        },
        {
            trigger: ".o_barcode_client_action",
            run: "scan P00001",
        },
        {
            trigger: '.o_barcode_client_action:contains("P00001")',
            run: "click",
        },
        {
            trigger: '.o_barcode_client_action:contains("Azure Interior")',
            run: "click",
        },
        ...stepUtils.validateBarcodeOperation(),
    ],
});

registry.category("web_tour.tours").add("test_inventory_using_buttons", {
    steps: () => [
        {
            trigger: ".o_button_inventory",
            run: "click",
        },

        // Scans product 1: must have 1 quantity and buttons +1/-1 must be visible.
        {
            trigger: ".o_barcode_client_action",
            run: "scan product1",
        },
        {
            trigger: ".o_barcode_client_action .o_barcode_line",
            run: function () {
                helper.assertLinesCount(1);
                const line = helper.getLine({ barcode: "product1" });
                helper.assertLineIsHighlighted(line, true);
                helper.assertLineQty(line, "1");
                helper.assertButtonIsVisible(line, "add_quantity");
                helper.assertButtonIsVisible(line, "remove_unit");
                helper.assertButtonIsVisible(line, "delete_line", false);
            },
        },
        // Clicks on -1 button: must have 0 quantity, -1 button should be hidden.
        {
            trigger: ".o_remove_unit",
            run: "click",
        },
        {
            trigger: '.o_barcode_line:contains("0")',
            run: function () {
                helper.assertLinesCount(1);
                const line = helper.getLine({ barcode: "product1" });
                helper.assertLineIsHighlighted(line, true);
                helper.assertLineQty(line, "0");
                helper.assertButtonIsVisible(line, "add_quantity");
                helper.assertButtonIsVisible(line, "remove_unit", false);
                helper.assertButtonIsVisible(line, "delete_line");
            },
        },
        // Clicks on +1 button: must have 1 quantity, -1 must be enabled now.
        {
            trigger: ".o_add_quantity",
            run: "click",
        },
        {
            trigger: '.o_barcode_line .qty-done:contains("1")',
            run: function () {
                helper.assertLinesCount(1);
                const line = helper.getLine({ barcode: "product1" });
                helper.assertLineIsHighlighted(line, true);
                helper.assertLineQty(line, "1");
                helper.assertButtonIsVisible(line, "add_quantity");
                helper.assertButtonIsVisible(line, "remove_unit");
                helper.assertButtonIsVisible(line, "delete_line", false);
            },
        },

        // Scans productserial1: must have 0 quantity.
        { trigger: ".o_barcode_client_action", run: "scan productserial1" },
        {
            trigger: ".o_barcode_client_action .o_barcode_line:nth-child(2)",
            run: function () {
                helper.assertLinesCount(2);
                const line = helper.getLine({ barcode: "productserial1", selected: true });
                helper.assertLineIsHighlighted(line, true);
                helper.assertLineQty(line, "0");
                // Should be visible because quantity is set.
                helper.assertButtonIsVisible(line, "unset");
                // Should be hide because quantity already on 0.
                helper.assertButtonIsVisible(line, "count_zero", false);
                // For tracked by SN product, should be visible when quantity = 0.
                helper.assertButtonIsVisible(line, "add_quantity");
                // Should be hide because qty is not greater than 0.
                helper.assertButtonIsVisible(line, "remove_unit", false);
                // SHould be visible because a line with 0 qty can be deleted.
                helper.assertButtonIsVisible(line, "delete_line");
                // Should be hide for product tracked by SN.
                helper.assertButtonIsVisible(line, "add_remaining_quantity", false);
            },
        },
        // Scans a serial number: must have 1 quantity, check button must display a "X".
        {
            trigger: ".o_barcode_client_action",
            run: "scan BNG-118",
        },
        {
            trigger: '.o_barcode_line:contains("BNG-118")',
            run: function () {
                helper.assertLinesCount(2);
                const line = helper.getLine({ barcode: "productserial1", selected: true });
                helper.assertLineIsHighlighted(line, true);
                helper.assertLineQty(line, "1");
                helper.assertButtonIsVisible(line, "count_zero", false);
                helper.assertButtonIsVisible(line, "unset");
                helper.assertButtonIsVisible(line, "remove_unit");
                helper.assertButtonIsVisible(line, "add_quantity", false);
            },
        },
        // Clicks on -1 button
        {
            trigger: '.o_barcode_line:contains("productserial1") button.o_remove_unit',
            run: "click",
        },
        {
            trigger: ".o_barcode_line.o_selected button.o_add_quantity",
            run: function () {
                helper.assertLinesCount(2);
                const line = helper.getLine({ barcode: "productserial1" });
                helper.assertLineIsHighlighted(line, true);
                helper.assertLineQty(line, "0");
                helper.assertButtonIsVisible(line, "count_zero", false);
                helper.assertButtonIsVisible(line, "unset");
                helper.assertButtonIsVisible(line, "remove_unit", false);
                helper.assertButtonIsVisible(line, "add_quantity");
            },
        },
        // Clicks on unset button.
        {
            trigger: '.o_barcode_line:contains("productserial1") button.o_unset',
            run: "click",
        },
        {
            trigger: '.o_barcode_line:contains("productserial1"):contains("?")',
            run: function () {
                helper.assertLinesCount(2);
                const line = helper.getLine({ barcode: "productserial1", selected: true });
                helper.assertLineIsHighlighted(line, true);
                helper.assertLineQty(line, "?");
                helper.assertButtonIsVisible(line, "count_zero");
                helper.assertButtonIsVisible(line, "unset", false);
                helper.assertButtonIsVisible(line, "remove_unit", false);
                helper.assertButtonIsVisible(line, "add_quantity");
            },
        },

        // Scans productlot1: must have 0 quantity, buttons should be visible.
        {
            trigger: ".o_barcode_client_action",
            run: "scan productlot1",
        },
        {
            trigger: ".o_barcode_client_action .o_barcode_line:nth-child(3)",
            run: function () {
                helper.assertLinesCount(3);
                const line = helper.getLine({ barcode: "productlot1" });
                helper.assertLineIsHighlighted(line, true);
                helper.assertLineQty(line, "0");
                helper.assertButtonIsVisible(line, "count_zero", false);
                helper.assertButtonIsVisible(line, "unset");
                helper.assertButtonIsVisible(line, "remove_unit", false);
                helper.assertButtonIsVisible(line, "add_quantity");
            },
        },
        // Scans a lot number: must have 1 quantity, buttons should still be visible.
        {
            trigger: ".o_barcode_client_action",
            run: "scan toto-42",
        },
        {
            trigger: '.o_barcode_line:contains("toto-42")',
            run: function () {
                helper.assertLinesCount(3);
                const line = helper.getLine({ barcode: "productlot1" });
                helper.assertLineIsHighlighted(line, true);
                helper.assertLineQty(line, "1");
                helper.assertButtonIsVisible(line, "count_zero", false);
                helper.assertButtonIsVisible(line, "unset");
                helper.assertButtonIsVisible(line, "remove_unit");
                helper.assertButtonIsVisible(line, "add_quantity");
            },
        },
        // Clicks on -1 button: must have 0 quantity, button -1 must be hide again.
        {
            trigger: '.o_barcode_line:contains("productlot1") .o_remove_unit',
            run: "click",
        },
        {
            trigger: '.o_barcode_line:contains("productlot1") .qty-done:contains("0")',
            run: function () {
                helper.assertLinesCount(3);
                const line = helper.getLine({ barcode: "productlot1" });
                helper.assertLineIsHighlighted(line, true);
                helper.assertLineQty(line, "0");
                helper.assertButtonIsVisible(line, "count_zero", false);
                helper.assertButtonIsVisible(line, "unset");
                helper.assertButtonIsVisible(line, "remove_unit", false);
                helper.assertButtonIsVisible(line, "add_quantity");
            },
        },
        // Clicks on +1 button: must have 1 quantity, buttons must be visible.
        {
            trigger: '.o_barcode_line:contains("productlot1") .o_add_quantity',
            run: "click",
        },
        {
            trigger: '.o_barcode_line:contains("productlot1") .qty-done:contains(1)',
            run: function () {
                helper.assertLinesCount(3);
                const line = helper.getLine({ barcode: "productlot1" });
                helper.assertLineIsHighlighted(line, true);
                helper.assertLineQty(line, "1");
                helper.assertButtonIsVisible(line, "count_zero", false);
                helper.assertButtonIsVisible(line, "unset");
                helper.assertButtonIsVisible(line, "remove_unit");
                helper.assertButtonIsVisible(line, "add_quantity");
            },
        },

        // Scans product2 => Should retrieve the quantity on hand and display 1/10.
        {
            trigger: ".o_barcode_client_action",
            run: "scan product2",
        },
        {
            trigger: '.o_barcode_line:contains("product2")',
            run: function () {
                helper.assertLinesCount(4);
                const line = helper.getLine({ barcode: "product2", selected: true });
                helper.assertLineIsHighlighted(line, true);
                helper.assertLineQty(line, "1/10");
                helper.assertButtonIsVisible(line, "count_zero", false);
                helper.assertButtonIsVisible(line, "unset");
                helper.assertButtonIsVisible(line, "remove_unit");
                helper.assertButtonIsVisible(line, "add_quantity");
            },
        },
        // Clicks multiple time on the set quantity button and checks the save is rightly done.
        {
            trigger: ".o_selected button.o_unset",
            run: "click",
        },
        {
            trigger: '.o_barcode_line:contains("product2"):contains("?")',
            run: function () {
                const line = helper.getLine({ barcode: "product2", selected: true });
                helper.assertLineQty(line, "?/10");
            },
        },
        // Goes to the quant form view to trigger a save then go back.
        {
            trigger: ".o_selected .o_line_button.o_edit",
            run: "click",
        },
        {
            trigger: ".o_discard",
            run: "click",
        },
        {
            trigger: '.o_barcode_line:contains("product2"):contains("?")',
            run: function () {
                const line = helper.getLine({ barcode: "product2" });
                helper.assertLineQty(line, "?/10");
            },
        },

        // Clicks again, should pass from  "? / 10" to "10 / 10"
        {
            trigger: '.o_barcode_line:contains("product2") button.o_add_remaining_quantity',
            run: "click",
        },
        {
            trigger: '.o_barcode_line:contains("product2") .qty-done:contains("10")',
            run: function () {
                const line = helper.getLine({ barcode: "product2" });
                helper.assertLineQty(line, "10/10");
            },
        },
        // Goes to the quant form view to trigger a save then go back.
        {
            trigger: '.o_barcode_line:contains("product2") .o_line_button.o_edit',
            run: "click",
        },
        {
            trigger: ".o_discard",
            run: "click",
        },
        {
            trigger: '.o_barcode_line:contains("product2") .qty-done:contains("10")',
            run: function () {
                const line = helper.getLine({ barcode: "product2" });
                helper.assertLineQty(line, "10/10");
            },
        },

        // Clicks again, should pass from  "10 / 10" to "? / 10"
        {
            trigger: '.o_barcode_line:contains("product2") button.o_unset',
            run: "click",
        },
        {
            trigger: '.o_barcode_line:contains("product2"):contains("?")',
            run: function () {
                const line = helper.getLine({ barcode: "product2" });
                helper.assertLineQty(line, "?/10");
            },
        },

        // Validates the inventory.
        {
            trigger: ".o_apply_page",
            run: "click",
        },
        {
            trigger: ".o_notification_bar.bg-success",
        },
    ],
});

registry.category("web_tour.tours").add("test_inventory_setting_show_quantity_to_count_on", {
    steps: () => [
        {
            trigger: ".o_button_inventory",
            run: "click",
        },
        {
            trigger: ".o_barcode_client_action",
            run: "scan LOC-01-00-00",
        },
        {
            trigger: ".o_scan_message.o_scan_product_or_src",
            run: function () {
                helper.assertLinesCount(3);
                const [line1, line2, line3] = helper.getLines();
                helper.assertLineProduct(line1, "product1");
                helper.assertLineProduct(line2, "productlot1");
                helper.assertLineProduct(line3, "productserial1");
                helper.assertButtonIsVisible(line1, "count_zero", false);
                helper.assertButtonIsVisible(line1, "add_quantity", false);
                helper.assertButtonIsVisible(line1, "remove_unit", false);
                helper.assertButtonIsVisible(line1, "add_remaining_quantity");
                helper.assertLineIsHighlighted(line1, false);
                helper.assertLineIsHighlighted(line2, false);
                helper.assertLineIsHighlighted(line3, false);
                helper.assertLineQty(line1, "?/5");
                helper.assertLineQty(line2, "?/7");
                helper.assertLineQty(line3, "?/3");
                helper.assertLineSourceLocation(line1, "WH/Stock");
                helper.assertLineSourceLocation(line2, "WH/Stock");
                helper.assertLineSourceLocation(line3, "WH/Stock");
            },
        },
        {
            trigger: '.o_barcode_line:contains("product1")',
            run: "click",
        },
        {
            trigger: '.o_barcode_line:contains("product1").o_selected',
            run: function () {
                const line = helper.getLine({ barcode: "product1" });
                helper.assertButtonIsVisible(line, "count_zero");
                helper.assertButtonIsVisible(line, "add_quantity");
                helper.assertButtonIsVisible(line, "remove_unit", false);
                helper.assertButtonIsVisible(line, "add_remaining_quantity");
            },
        },
        {
            trigger: ".o_barcode_line.o_selected .o_line_button.o_edit",
            run: "click",
        },
        {
            trigger: '.o_digipad_fufill:contains("5")',
        },
        {
            content: "Check button to add expected quantity is visible",
            trigger: ".o_barcode_control .o_discard",
            run: "click",
        },
        {
            trigger: '.o_barcode_line:contains("productlot1")',
            run: "click",
        },
        {
            trigger: ".o_barcode_line.o_selected .o_line_button.o_toggle_sublines",
            run: function () {
                helper.assertSublinesCount(2);
                const sublines = helper.getSublines();
                helper.assertLineQty(sublines[0], "?/3");
                helper.assertLineQty(sublines[1], "?/4");
                helper.assertLinesTrackingNumbers(sublines, ["lot1", "lot2"]);
                helper.assertButtonIsVisible(sublines[0], "count_zero");
                helper.assertButtonIsVisible(sublines[0], "remove_unit", false);
                helper.assertButtonIsVisible(sublines[0], "add_quantity");
                helper.assertButtonIsVisible(sublines[0], "add_remaining_quantity");
                helper.assertButtonIsVisible(sublines[1], "count_zero", false);
                helper.assertButtonIsVisible(sublines[1], "remove_unit", false);
                helper.assertButtonIsVisible(sublines[1], "add_quantity", false);
                helper.assertButtonIsVisible(sublines[1], "add_remaining_quantity");
            },
        },
        {
            trigger: '.o_barcode_line:contains("productserial1")',
            run: "click",
        },
        {
            trigger: ".o_barcode_line.o_selected .o_line_button.o_toggle_sublines .fa-angle-up",
            run: function () {
                helper.assertSublinesCount(3);
                const sublines = helper.getSublines();
                helper.assertLineQty(sublines[0], "?/1");
                helper.assertLineQty(sublines[1], "?/1");
                helper.assertLineQty(sublines[2], "?/1");
                helper.assertLinesTrackingNumbers(sublines, ["sn1", "sn2", "sn3"]);
                helper.assertButtonIsVisible(sublines[0], "count_zero");
                helper.assertButtonIsVisible(sublines[0], "remove_unit", false);
                helper.assertButtonIsVisible(sublines[0], "add_quantity", false);
                helper.assertButtonIsVisible(sublines[0], "add_remaining_quantity");
                helper.assertButtonIsVisible(sublines[1], "count_zero", false);
                helper.assertButtonIsVisible(sublines[1], "remove_unit", false);
                helper.assertButtonIsVisible(sublines[1], "add_quantity", false);
                helper.assertButtonIsVisible(sublines[1], "add_remaining_quantity");
                helper.assertButtonIsVisible(sublines[2], "count_zero", false);
                helper.assertButtonIsVisible(sublines[2], "remove_unit", false);
                helper.assertButtonIsVisible(sublines[2], "add_quantity", false);
                helper.assertButtonIsVisible(sublines[2], "add_remaining_quantity");
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_inventory_setting_show_quantity_to_count_off", {
    steps: () => [
        {
            trigger: ".o_button_inventory",
            run: "click",
        },
        {
            trigger: ".o_barcode_client_action",
            run: "scan LOC-01-00-00",
        },
        {
            trigger: ".o_scan_message.o_scan_product_or_src",
            run: function () {
                helper.assertLinesCount(3);
                const [line1, line2, line3] = helper.getLines();
                helper.assertLineProduct(line1, "product1");
                helper.assertLineProduct(line2, "productlot1");
                helper.assertLineProduct(line3, "productserial1");
                helper.assertButtonIsVisible(line1, "set", false);
                helper.assertLineIsHighlighted(line1, false);
                helper.assertLineIsHighlighted(line2, false);
                helper.assertLineIsHighlighted(line3, false);
                helper.assertLineQty(line1, "?");
                helper.assertLineQty(line2, "?");
                helper.assertLineQty(line3, "?");
                helper.assertLineSourceLocation(line1, "WH/Stock");
                helper.assertLineSourceLocation(line2, "WH/Stock");
                helper.assertLineSourceLocation(line3, "WH/Stock");
            },
        },
        {
            trigger: '.o_barcode_line:contains("product1")',
            run: "click",
        },
        {
            trigger: '.o_barcode_line:contains("product1").o_selected',
            run: function () {
                const line = helper.getLine({ barcode: "product1" });
                helper.assertButtonIsVisible(line, "count_zero");
                helper.assertButtonIsVisible(line, "remove_unit", false);
                helper.assertButtonIsVisible(line, "add_quantity");
                helper.assertButtonIsVisible(line, "add_remaining_quantity", false);
            },
        },
        {
            trigger: ".o_barcode_line.o_selected .o_line_button.o_edit",
            run: "click",
        },
        {
            trigger: ".o_form_view_container",
            run: function () {
                helper.assert(
                    Boolean(document.querySelector(".o_digipad_fufill")),
                    false,
                    "Button to set counted quantity shouldn't be visible"
                );
            },
        },
        {
            trigger: ".o_barcode_control .o_discard",
            run: "click",
        },

        {
            trigger: '.o_barcode_line:contains("productlot1")',
            run: "click",
        },
        {
            trigger: ".o_barcode_line.o_selected .o_line_button.o_toggle_sublines",
            run: function () {
                helper.assertSublinesCount(2);
                const [subline1, subline2] = helper.getSublines();
                helper.assertLineQty(subline1, "?");
                helper.assertLineQty(subline2, "?");
                helper.assert(subline1.querySelector(".o_line_lot_name").innerText, "lot1");
                helper.assert(subline2.querySelector(".o_line_lot_name").innerText, "lot2");
                helper.assertButtonIsVisible(subline1, "count_zero");
                helper.assertButtonIsVisible(subline1, "remove_unit", false);
                helper.assertButtonIsVisible(subline1, "add_quantity");
                helper.assertButtonIsVisible(subline1, "add_remaining_quantity", false);
                helper.assertButtonIsVisible(subline2, "count_zero", false);
                helper.assertButtonIsVisible(subline2, "remove_unit", false);
                helper.assertButtonIsVisible(subline2, "add_quantity", false);
                helper.assertButtonIsVisible(subline2, "add_remaining_quantity", false);
            },
        },
        {
            trigger: '.o_barcode_line:contains("productserial1")',
            run: "click",
        },
        {
            trigger: ".o_barcode_line.o_selected .o_line_button.o_toggle_sublines .fa-angle-up",
            run: function () {
                helper.assertSublinesCount(3);
                const [subline1, subline2, subline3] = helper.getSublines();
                helper.assertLineQty(subline1, "?");
                helper.assertLineQty(subline2, "?");
                helper.assertLineQty(subline3, "?");
                helper.assert(subline1.querySelector(".o_line_lot_name").innerText, "sn1");
                helper.assert(subline2.querySelector(".o_line_lot_name").innerText, "sn2");
                helper.assert(subline3.querySelector(".o_line_lot_name").innerText, "sn3");
                // For product tracked by SN, the set button should be visible no matter the parameter.
                helper.assertButtonIsVisible(subline1, "count_zero");
                helper.assertButtonIsVisible(subline1, "remove_unit", false);
                helper.assertButtonIsVisible(subline1, "add_quantity");
                helper.assertButtonIsVisible(subline1, "add_remaining_quantity", false);
                helper.assertButtonIsVisible(subline2, "count_zero", false);
                helper.assertButtonIsVisible(subline2, "remove_unit", false);
                helper.assertButtonIsVisible(subline2, "add_quantity", false);
                helper.assertButtonIsVisible(subline2, "add_remaining_quantity", false);
                helper.assertButtonIsVisible(subline3, "count_zero", false);
                helper.assertButtonIsVisible(subline3, "remove_unit", false);
                helper.assertButtonIsVisible(subline3, "add_quantity", false);
                helper.assertButtonIsVisible(subline3, "add_remaining_quantity", false);
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_inventory_setting_count_entire_locations_on", {
    steps: () => [
        {
            trigger: ".o_button_inventory",
            run: "click",
        },
        // At first, only the marked as to count quant should be visible.
        {
            trigger: ".o_barcode_client_action",
            run: function () {
                helper.assertLinesCount(1);
                const line = helper.getLine();
                helper.assertLineProduct(line, "product1");
                helper.assertLineQty(line, "10/10");
                helper.assertLineSourceLocation(line, "WH/Stock/Section 1");
            },
        },
        // Scan WH/Stock/Section 1 => Should fetch all quants in this location.
        {
            trigger: ".o_barcode_client_action",
            run: "scan LOC-01-01-00",
        },
        // Check that all quants of WH/Stock/Section 1 are loaded with their respective information.
        {
            trigger: ".o_barcode_line:nth-child(4)",
            run: function () {
                helper.assertLinesCount(4);
                const [line1, line2, line3, line4] = helper.getLines();
                helper.assertLineProduct(line1, "product1");
                helper.assertLineProduct(line2, "product2");
                helper.assertLineProduct(line3, "productlot1");
                helper.assertLineProduct(line4, "productserial1");
                helper.assertLineQty(line1, "10/10");
                helper.assertLineQty(line2, "?/20");
                helper.assertLineQty(line3, "?/7");
                helper.assertLineQty(line4, "?/3");
                helper.assertLineSourceLocation(line1, "WH/Stock/Section 1");
                helper.assertLineSourceLocation(line2, "WH/Stock/Section 1");
                helper.assertLineSourceLocation(line3, "WH/Stock/Section 1");
                helper.assertLineSourceLocation(line4, "WH/Stock/Section 1");
            },
        },

        // Scan WH/Stock/Section 2 => Should fetch all quants in this location.
        {
            trigger: ".o_barcode_client_action",
            run: "scan LOC-01-02-00",
        },
        // Check that all quants of WH/Stock/Section 2 are loaded with their respective information.
        {
            trigger: '.o_barcode_location_line[data-location="WH/Stock/Section 2"].text-bg-800',
            run: function () {
                helper.assertLinesCount(7);
                helper.assertLineProduct(4, "[TEST] product1");
                helper.assertLineQty(4, "?/30");
                helper.assertLineSourceLocation(4, "WH/Stock/Section 2");
                helper.assertLineProduct(5, "productlot1");
                helper.assertLineQty(5, "?/7");
                helper.assertLineSourceLocation(5, "WH/Stock/Section 2");
                helper.assertLineProduct(6, "productserial1");
                helper.assertLineQty(6, "?/3");
                helper.assertLineSourceLocation(6, "WH/Stock/Section 2");
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_inventory_setting_count_entire_locations_off", {
    steps: () => [
        {
            trigger: ".o_button_inventory",
            run: "click",
        },
        // Only the marked as to count quant should be visible.
        {
            trigger: ".o_barcode_client_action",
            run: function () {
                helper.assertLinesCount(1);
                helper.assertLineProduct(0, "product1");
                helper.assertLineQty(0, "10/10");
                helper.assertLineSourceLocation(0, "WH/Stock/Section 1");
            },
        },
        // Scan WH/Stock/Section 1 => Should not fetch other quants.
        {
            trigger: ".o_barcode_client_action",
            run: "scan LOC-01-01-00",
        },
        {
            trigger: ".o_barcode_location_line.text-bg-800",
            run: function () {
                helper.assertLinesCount(1);
                helper.assertLineProduct(0, "product1");
                helper.assertLineQty(0, "10/10");
                helper.assertLineSourceLocation(0, "WH/Stock/Section 1");
            },
        },
    ],
});

registry
    .category("web_tour.tours")
    .add("test_inventory_adjustment_with_no_internal_location_quant", {
        steps: () => [
            {
                trigger: ".o_button_inventory",
                run: "click",
            },
            {
                trigger: ".o_barcode_client_action",
                run: "scan product1",
            },
            {
                trigger: ".o_barcode_line",
                run: () => {
                    helper.assertLineSourceLocation(0, "WH/Stock");
                    helper.assertLineProduct(0, "product1");
                    helper.assertLineQty(0, "1");
                },
            },
            {
                trigger: ".o_apply_page.btn-primary",
                run: "click",
            },
            {
                trigger: ".o_notification_bar.bg-success",
                run: function () {
                    helper.assertErrorMessage("The inventory count has been updated");
                },
            },
        ],
    });

registry.category("web_tour.tours").add("test_correct_inventory_with_packages", {
    steps: () => [
        {
            trigger: ".o_button_inventory",
            run: "click",
        },
        {
            trigger: ".o_barcode_client_action",
            run: "scan Shelf11",
        },
        {
            trigger: ".o_barcode_line",
            run: "click",
        },
        {
            trigger: ".o_barcode_line_details",
            run: function () {
                helper.assertLinesCount(1);
                helper.assertLineProduct(0, "Product");
                helper.assertLineQty(0, "?/10");
                const [subline1, subline2] = helper.getSublines();
                helper.assertLineQty(subline1, "?/5");
                helper.assertLineQty(subline2, "?/5");
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_inventory_count_with_line_deletion", {
    steps: () => [
        {
            trigger: ".o_button_inventory",
            run: "click",
        },
        {
            trigger: ".o_barcode_client_action",
            run: "scan product1",
        },
        {
            trigger: ".o_barcode_line",
            run: function () {
                helper.assertLinesCount(1);
                helper.assertLineProduct(0, "product1");
                helper.assertLineQty(0, "1/5");
            },
        },
        {
            trigger: ".o_remove_unit",
            run: "click",
        },
        {
            trigger: ".o_delete_line",
            run: "click",
        },
        {
            trigger: ".o_barcode_client_action:not(:has(.o_barcode_line))",
            run: "scan product1",
        },
        {
            trigger: ".o_barcode_line",
            run: function () {
                helper.assertLinesCount(1);
                helper.assertLineProduct(0, "product1");
                helper.assertLineQty(0, "1");
            },
        },
    ],
});
