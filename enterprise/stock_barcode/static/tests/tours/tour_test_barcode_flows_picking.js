/** @odoo-module */

import * as helper from './tour_helper_stock_barcode';
import { registry } from "@web/core/registry";
import { stepUtils } from "./tour_step_utils";

registry.category("web_tour.tours").add('test_internal_picking_from_scratch', { steps: () => [
    // Move 2 product1 from WH/Stock/Section 1 to WH/Stock/Section 2.
    {
        trigger: '.o_add_line',
        run: "click",
    },
    {
        trigger: '.o_field_widget[name="product_id"]',
    },
    {
        trigger: ".o_field_widget[name=qty_done] input",
        run: "edit 2",
    },

    {
        trigger: ".o_field_widget[name=product_id] input",
        run: "edit product1",
    },

    {
        trigger: ".ui-menu-item > a:contains('product1')",
        run: "click",
    },

    {
        trigger: ".o_field_widget[name=location_id] input",
        run: "edit Section 1",
    },

    {
        trigger: ".ui-menu-item > a:contains('Section 1')",
        run: "click",
    },

    {
        trigger: ".o_field_widget[name=location_dest_id] input",
        run: "edit Section 2",
    },

    {
        trigger: ".ui-menu-item > a:contains('Section 2')",
        run: "click",
    },

    {
        trigger: '.o_save',
        run: "click",
    },
    {
        trigger: '.o_barcode_line .o_line_destination_location:contains("Section 2")',
    },
    {
        trigger: '.o_barcode_location_line[data-location="WH/Stock/Section 1"] + .o_barcode_line',
        run: function() {
            helper.assertLinesCount(1);
        },
    },

    // Move 1 product2 from WH/Stock/Section 1 to WH/Stock/Section 3.
    {
        trigger: '.o_add_line',
        run: "click",
    },
    {
        trigger: '.o_field_widget[name="product_id"]',
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
        trigger: ".o_field_widget[name=location_id] input",
        run: "edit Section 1",
    },

    {
        trigger: ".ui-menu-item > a:contains('Section 1')",
        run: "click",
    },

    {
        trigger: ".o_field_widget[name=location_dest_id] input",
        run: "edit WH/Stock/Section 3",
    },

    {
        trigger: ".ui-menu-item > a:contains('Section 3')",
        run: "click",
    },

    {
        trigger: '.o_save',
        run: "click",
    },
    {
        trigger: '.o_barcode_line .o_line_destination_location:contains("Section 3")',
    },
    {
        trigger: '.o_barcode_location_line[data-location="WH/Stock/Section 1"] + .o_barcode_line + .o_barcode_line',
        run: function() {
            helper.assertLinesCount(2);
            const lineProduct1 = helper.getLine({ barcode: "product1" });
            helper.assertLineIsHighlighted(lineProduct1, false);
            const lineProduct2 = helper.getLine({ barcode: "product2" });
            helper.assertLineIsHighlighted(lineProduct2, true);
        },
    },

    // Edits the first line to check the transaction doesn't crash and the form view is correctly filled.
    {
        trigger: '.o_barcode_line:nth-child(2) .o_edit',
        run: "click",
    },
    {
        trigger: '.o_field_widget[name="product_id"]',
        run: function() {
            helper.assertFormLocationSrc("WH/Stock/Section 1");
            helper.assertFormLocationDest("WH/Stock/Section 2");
            helper.assertFormQuantity("2");
        },
    },

    {
        trigger: '.o_save',
        run: "click",
    },

    // Move 1 product2 from WH/Stock/Section 1 to WH/Stock/Section 2.
    {
        trigger: '.o_add_line',
        run: "click",
    },
    {
        trigger: '.o_field_widget[name="product_id"]',
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
        trigger: ".o_field_widget[name=location_id] input",
        run: "edit Section 1",
    },

    {
        trigger: ".ui-menu-item > a:contains('Section 1')",
        run: "click",
    },

    {
        trigger: ".o_field_widget[name=location_dest_id] input",
        run: "edit Section 2",
    },

    {
        trigger: ".ui-menu-item > a:contains('Section 2')",
        run: "click",
    },

    {
        trigger: '.o_save',
        run: "click",
    },
    {
        trigger: '.o_barcode_line.o_selected .o_line_destination_location:contains("Section 2")',
    },
    {
        trigger: '.o_barcode_location_group .o_barcode_line:nth-child(4)',
        run: function() {
            helper.assertLinesCount(3);
        },
    },
    // Scans the destination (Section 2) for the current line...
    {
        trigger: '.o_barcode_line:nth-child(3).o_selected',
        run: 'scan LOC-01-02-00',
    },
    // ...then scans the source (Section 1) for the next line.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-01-00',
    },
    // On this page, scans product1 which will create a new line and then opens its edit form view.

    {
        trigger: '.o_barcode_location_line[data-location="WH/Stock/Section 1"].text-bg-800',
        run: 'scan product1'
    },

    { // First call to write.
        trigger: '.o_barcode_line[data-barcode="product1"].o_selected .o_edit',
        run: "click",
    },
    {
        trigger: '.o_field_widget[name="product_id"]:contains("product1")',
    },
    {
        trigger:'.o_save',
        run: "click",
    },
    { // Scans the line's destination before to validate the picking.
        trigger: '.o_barcode_line[data-barcode="product1"].o_selected',
        run: 'scan shelf3',
    },
    {
        trigger: '.o_barcode_line:nth-child(2) .o_line_destination_location:contains("Section 3")',
    },
    {
        trigger: '.o_validate_page',
        run: "click",
    },
    { // Second call to write (change the dest. location).
        trigger: '.o_notification_bar.bg-success',
    }
]});

registry.category("web_tour.tours").add('test_internal_picking_from_scratch_with_package', {  steps: () => [
    // Creates a first internal transfert (Section 1 -> Section 2).
    { trigger: '.o_stock_barcode_main_menu', run: 'scan WHINT' },
    // Scans product1 and put it in P00001, then do the same for product2.
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    { trigger: '.o_barcode_line.o_selected', run: 'scan P00001' },
    // Scans the destination.
    { trigger: '.o_barcode_line .result-package', run: 'scan LOC-01-02-00' },
    { trigger: '.o_barcode_line:not(.o_selected)', run: 'scan product2' },
    { trigger: '.o_barcode_line[data-barcode="product2"].o_selected', run: 'scan P00001' },
    { // Scans the destination.
        trigger: '.o_barcode_line[data-barcode="product2"] .result-package', run: 'scan LOC-01-02-00',
    },
    { // Validates the internal picking.
        trigger: '.o_barcode_line[data-barcode="product2"] .o_line_destination_location',
        run: 'scan OBTVALI',
    },
    {
        trigger: '.o_notification_bar.bg-success',
        run: "click",
    },
    {
        trigger: '.o_notification button.o_notification_close',
        run: "click",
    },

    // Creates a second internal transfert (WH/Stock -> WH/Stock).
    { trigger: '.o_stock_barcode_main_menu', run: 'scan WHINT' },
    { trigger: '.o_barcode_client_action', run: () => helper.assertLinesCount(0) },
    // Scans a package with some quants and checks lines was created for its content.
    { trigger: '.o_barcode_client_action', run: 'scan P00002' },
    {
        trigger: '.o_barcode_line[data-barcode="product1"] + .o_barcode_line[data-barcode="product2"]',
        run: () => {
            helper.assertLinesCount(2);
            helper.assertLineQty(0, "1");
            helper.assertLineQty(1, "2");
        },
    },
    // Scans the destination location and validate the transfert.
    { trigger: '.o_barcode_line.o_selected + .o_barcode_line.o_selected', run: 'scan LOC-01-02-00' },
    { trigger: '.o_barcode_line:not(.o_selected)', run: 'scan OBTVALI' },
    { trigger: '.o_notification_bar.bg-success'},
]});

registry.category("web_tour.tours").add("test_internal_pack_in_same_package", {
    steps: () => [
        // 1st transfer: scan a product and pack it into an existing empty package.
        { trigger: ".o_stock_barcode_main_menu", run: "scan WHINT" },
        { trigger: ".o_scan_message.o_scan_product", run: "scan pack1" },
        { trigger: ".o_barcode_line", run: "scan pack3" },
        {
            trigger: ".result-package:contains('pack3')",
            run: () => {
                helper.assertLinesCount(1);
                helper.assertLineProduct(0, "[TEST] product1");
                helper.assertLinePackage(0, "pack1");
                helper.assertLineResultPackage(0, "pack3");
            },
        },
        ...stepUtils.validateBarcodeOperation(),

        // 2nd transfer: scan a product and pack it into the same package (which has content now.)
        { trigger: ".o_stock_barcode_main_menu", run: "scan WHINT" },
        { trigger: ".o_scan_message.o_scan_product", run: "scan pack2" },
        { trigger: ".o_barcode_line", run: "scan pack3" },
        {
            trigger: ".result-package:contains('pack3')",
            run: () => {
                helper.assertLinesCount(1);
                helper.assertLineProduct(0, "product2");
                helper.assertLinePackage(0, "pack2");
                helper.assertLineResultPackage(0, "pack3");
            },
        },
        ...stepUtils.validateBarcodeOperation(),
        { trigger: ".o_stock_barcode_main_menu" },
    ],
});

registry.category("web_tour.tours").add('test_internal_picking_reserved_1', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(3);
            helper.assertScanMessage('scan_src');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
            helper.assertLineIsHighlighted(0, false);
            helper.assertLineLocations(0, 'WH/Stock/Section 1', '.../Section 2');
            helper.assertLineIsHighlighted(1, false);
            helper.assertLineLocations(1, 'WH/Stock/Section 1', '.../Section 2');
            helper.assertLineIsHighlighted(2, false);
            helper.assertLineLocations(2, 'WH/Stock/Section 3', '.../Section 4');
        }
    },

    // We first move a product1 from shef3 to shelf2.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan shelf3'
    },

    {
        trigger: '.o_barcode_location_line[data-location="WH/Stock/Section 3"].text-bg-800',
        run: function() {
            helper.assertLinesCount(3);
            helper.assertScanMessage('scan_product');
            const locationInBold = document.querySelector('.o_barcode_location_line.text-bg-800');
            const lineInSection3 = locationInBold.parentElement.querySelector('.o_barcode_line');
            helper.assertLineLocations(lineInSection3, 'WH/Stock/Section 3', '.../Section 4');
        }
    },

    // Scan product1 after scanned shelf3 will select the existing line but change its source.
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: function() {
            helper.assertLinesCount(3);
            helper.assertScanMessage('scan_dest');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
            const lineproduct1 = helper.getLine({ selected: true });
            helper.assertLineIsHighlighted(lineproduct1, true);
            helper.assertLineLocations(lineproduct1, 'WH/Stock/Section 3', '.../Section 2');
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-02-00'
    },

    {
        trigger: '.o_barcode_location_group:nth-child(2) .o_barcode_line:not(.o_selected):nth-child(2) .o_line_destination_location:contains(".../Section 2")',
        run: function() {
            helper.assertLinesCount(3);
            helper.assertScanMessage('scan_src');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
            const lineproduct1 = helper.getLine({barcode: 'product1'});
            helper.assertLineIsHighlighted(lineproduct1, false);
            helper.assertLineLocations(lineproduct1, 'WH/Stock/Section 3', '.../Section 2');
        }
    },

    // Scans Section 1 as source location.
    { 'trigger': '.o_barcode_client_action', run: 'scan LOC-01-01-00' },

    {
        trigger: '.o_barcode_location_line[data-location="WH/Stock/Section 1"].text-bg-800',
        run: function() {
            helper.assertLinesCount(3);
            helper.assertScanMessage('scan_product');
            helper.assertLineIsHighlighted(0, false);
            helper.assertLineIsHighlighted(1, false);
            helper.assertLineIsHighlighted(2, false);
        }
    },

    // Process the reservation for product1 (create a new line as the previous one was overrided).
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    {
        trigger: '.o_barcode_location_group:first-child .o_barcode_line.o_selected',
        run: function() {
            helper.assertLinesCount(4);
            helper.assertScanMessage('scan_product_or_dest');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
            helper.assertLineIsHighlighted(0, false);
            helper.assertLineIsHighlighted(1, true);
            helper.assertLineLocations(1, 'WH/Stock/Section 1', 'WH/Stock');
            helper.assertLineIsHighlighted(2, false);
            helper.assertLineIsHighlighted(3, false);
        }
    },
    { trigger: '.o_barcode_client_action', run: 'scan LOC-01-02-00' },

    // Process the reservation for product2 (Section 1 to Section 2).
    { trigger: '.o_scan_message.o_scan_src', run: 'scan LOC-01-01-00' },
    { trigger: '.o_scan_message.o_scan_product', run: 'scan product2' },
    {
        trigger: '.o_barcode_location_group:first-child .o_barcode_line:nth-child(2).o_selected',
        run: function() {
            helper.assertLinesCount(4);
            helper.assertScanMessage('scan_dest');
            helper.assertValidateIsHighlighted(false);
            helper.assertLineIsHighlighted(0, true);
            helper.assertLineIsHighlighted(1, false);
            helper.assertLineIsHighlighted(2, false);
            helper.assertLineIsHighlighted(3, false);
        }
    },
    { trigger: '.o_barcode_client_action', run: 'scan LOC-01-02-00' },

    // Process the reservation for product2 (Section 3 to Section 4).
    { trigger: '.o_scan_message.o_scan_src', run: 'scan shelf3' },
    { trigger: '.o_scan_message.o_scan_product', run: 'scan product2' },
    {
        trigger: '.o_barcode_location_group:nth-child(2) .o_barcode_line:nth-child(3).o_selected',
        run: function() {
            helper.assertLinesCount(4);
            helper.assertScanMessage('scan_dest');
            helper.assertValidateIsHighlighted(false);
            helper.assertLineIsHighlighted(0, false);
            helper.assertLineIsHighlighted(1, false);
            helper.assertLineIsHighlighted(2, false);
            helper.assertLineIsHighlighted(3, true);
        }
    },
    { trigger: '.o_scan_message.o_scan_dest', run: 'scan shelf4' },

    {
        trigger: '.o_scan_message.o_scan_validate',
        run: function() {
            helper.assertLinesCount(4);
            helper.assertScanMessage('scan_validate');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(true);
            helper.assertValidateEnabled(true);

            helper.assertLineIsHighlighted(0, false);
            helper.assertLineQty(0, '1/1');
            helper.assertLineLocations(0, 'WH/Stock/Section 1', '.../Section 2');

            helper.assertLineIsHighlighted(1, false);
            helper.assertLineQty(1, '1');
            helper.assertLineLocations(1, 'WH/Stock/Section 1', '.../Section 2');

            helper.assertLineIsHighlighted(2, false);
            helper.assertLineQty(2, '1/1');
            helper.assertLineLocations(2, 'WH/Stock/Section 3', '.../Section 2');

            helper.assertLineIsHighlighted(3, false);
            helper.assertLineQty(3, '1/1');
            helper.assertLineLocations(3, 'WH/Stock/Section 3', '.../Section 4');
        }
    },
]});

registry.category("web_tour.tours").add('test_procurement_backorder', { steps: () => [
        { trigger: '.o_barcode_client_action', run: 'scan PB' },
        { trigger: '.o_barcode_line:contains("PB")', run: 'scan OBTVALI' },
        { trigger: '.o_notification_bar.bg-success'},
    ]
});

registry.category("web_tour.tours").add('test_receipt_reserved_1', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(2);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2'
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2'
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2'
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2'
    },

    // Try to scan WH/Stock 2 as the destination -> Should display an error notification.
    { trigger: '.o_barcode_line.o_selected.o_line_completed', run: 'scan WHSTOCK-2' },
    {
        trigger: '.o_notification_bar.bg-danger',
        run: () => {
            helper.assertErrorMessage("The scanned location doesn't belong to this operation's destination");
    }},
    // Scan Shelf1 as scanned product2 destination.
    { trigger: '.o_barcode_client_action', run: 'scan LOC-01-01-00' },

    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan product1'
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertValidateIsHighlighted(false);
        }
    },

    ...stepUtils.inputManuallyBarcode("product1"),

    {
        trigger: '.o_barcode_line[data-barcode="product1"] .qty-done:contains("4")',
        run: function() {
            helper.assertValidateIsHighlighted(true);
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-01-00'
    },

    {
        trigger: '.o_scan_message.o_scan_validate',
        run: function() {
            helper.assertLinesCount(2);
            helper.assertScanMessage('scan_validate');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(true);
            helper.assertValidateEnabled(true);
        }
    },

    {
        trigger: '.o_add_line',
        run: "click",
    },
    {
        trigger: '.o_field_widget[name="product_id"]',
        run: function() {
            helper.assertFormLocationDest('WH/Stock');
        },
    },
    ...stepUtils.discardBarcodeForm(),
]});

registry.category("web_tour.tours").add('test_receipt_reserved_2_partial_put_in_pack', { steps: () => [
    // Scan the picking's name to open it.
    { trigger: '.o_stock_barcode_main_menu', run: 'scan receipt_test' },
    {
        trigger: '.o_barcode_line',
        run: function() {
            helper.assertLinesCount(2);
            helper.assertLineProduct(0, "product1");
            helper.assertLineQty(0, "0/3");
            helper.assertLineProduct(1, "product2");
            helper.assertLineQty(1, "0/3");
        },
    },

    // Scan 2x product1 then put in pack.
    { trigger: '.o_barcode_client_action', run: 'scan product1'},
    { trigger: '.o_barcode_client_action', run: 'scan product1'},
    {
        trigger: '.o_barcode_line.o_selected .qty-done:contains("2")',
        run: function() {
            helper.assertLinesCount(2);
            helper.assertLineProduct(0, "product1");
            helper.assertLineQty(0, "2/3");
            helper.assertLineProduct(1, "product2");
            helper.assertLineQty(1, "0/3");
        },
    },
    { trigger: '.o_barcode_client_action', run: 'scan OBTPACK'},
    {
        trigger: '.o_barcode_line:contains("PACK0001000")',
        run: function() {
            const lines = helper.getLines();
            helper.assert(lines.length, 3);

            helper.assertLineProduct(lines[0], "product1");
            helper.assertLineQty(lines[0], "0/1");
            helper.assert(lines[0].querySelector('.result-package'), null);

            helper.assertLineProduct(lines[1], "product2");
            helper.assertLineQty(lines[1], "0/3");
            helper.assert(lines[1].querySelector('.result-package'), null);

            helper.assertLineProduct(lines[2], "product1");
            helper.assertLineQty(lines[2], "2/2");
            helper.assert(lines[2].querySelector('.result-package').innerText, "PACK0001000");
        },
    },

    // Scan product1 and product2 then put in pack.
    { trigger: '.o_barcode_client_action', run: 'scan product1'},
    { trigger: '.o_barcode_line:first-child.o_selected.o_line_completed', run: 'scan product2'},
    {
        trigger: '.o_barcode_line[data-barcode="product2"].o_selected .qty-done:contains("1")',
        run: function() {
            const lines = helper.getLines();
            helper.assert(lines.length, 3);

            helper.assertLineProduct(lines[0], "product1");
            helper.assertLineQty(lines[0], "1/1");
            helper.assert(lines[0].querySelector('.result-package'), null);

            helper.assertLineProduct(lines[1], "product2");
            helper.assertLineQty(lines[1], "1/3");
            helper.assert(lines[1].querySelector('.result-package'), null);

            helper.assertLineProduct(lines[2], "product1");
            helper.assertLineQty(lines[2], "2/2");
            helper.assert(lines[2].querySelector('.result-package').innerText, "PACK0001000");
        },
    },
    {
        trigger: '.o_put_in_pack',
        run: "click",
    },
    {
        trigger: '.o_barcode_line:contains("PACK0001001")',
        run: function() {
            const lines = helper.getLines();
            helper.assert(lines.length, 4);

            helper.assertLineProduct(lines[0], "product2");
            helper.assertLineQty(lines[0], "0/2");
            helper.assert(lines[0].querySelector('.result-package'), null);

            helper.assertLineProduct(lines[1], "product1");
            helper.assertLineQty(lines[1], "2/2");
            helper.assert(lines[1].querySelector('.result-package').innerText, "PACK0001000");

            helper.assertLineProduct(lines[2], "product1");
            helper.assertLineQty(lines[2], "1/1");
            helper.assert(lines[2].querySelector('.result-package').innerText, "PACK0001001");

            helper.assertLineProduct(lines[3], "product2");
            helper.assertLineQty(lines[3], "1/1");
            helper.assert(lines[3].querySelector('.result-package').innerText, "PACK0001001");
        },
    },
    // Confirm the backorder, then close the receipt.
    { trigger: '.btn.o_validate_page', run: 'click' },
    { trigger: '.modal-dialog button.btn-primary', run: 'click' },
    { trigger: '.o_stock_barcode_main_menu' },
]});

registry.category("web_tour.tours").add('test_receipt_product_not_consecutively', { steps: () => [
    // Scan two products (product1 - product2 - product1)
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    { trigger: '.o_barcode_line', run: 'scan product2' },
    { trigger: '.o_barcode_line:contains("product2")', run: 'scan product1' },
    {
        trigger: '.o_barcode_line[data-barcode="product1"] .qty-done:contains("2")',
        run: 'scan OBTVALI',
    },
    {
        trigger: '.o_notification_bar.bg-success',
    },
]});

registry.category("web_tour.tours").add("test_delivery_source_location", { steps: () => [
    // FIRST DELIVERY (using stock from WH/Stock)
    { trigger: ".o_stock_barcode_main_menu", run: 'scan delivery_from_stock' },
    // Tries to scan a location who doesn't belong to the delivery's source location.
    { trigger: '.o_scan_message.o_scan_src', run: 'scan WH-SECOND-STOCK' },
    {
        trigger: '.o_notification_bar.bg-danger',
        run: () => {
            helper.assertErrorMessage("The scanned location doesn't belong to this operation's location");
    }},
    {
        trigger: 'button.o_notification_close',
        run: "click",
    },
    // Scans the right location now.
    { trigger: '.o_barcode_client_action', run: 'scan LOC-01-00-00' },
    { trigger: '.o_scan_message.o_scan_product', run: 'scan product1' },
    { trigger: '.o_barcode_line.o_selected', run: 'scan product1' },
    { trigger: '.o_barcode_line.o_selected', run: 'scan product1' },
    { trigger: '.o_barcode_line.o_selected', run: 'scan product1' },
    {
        trigger: '.o_validate_page.btn-primary',
        run: "click",
    },

    // SECOND DELIVERY (using stock from WH/Second Stock)
    { trigger: ".o_stock_barcode_main_menu", run: 'scan delivery_from_second_stock' },
    // Tries to scan a location who doesn't belong to the delivery's source location.
    { trigger: '.o_scan_message.o_scan_src', run: 'scan LOC-01-00-00' },
    {
        trigger: '.o_notification_bar.bg-danger',
        run: () => {
            helper.assertErrorMessage("The scanned location doesn't belong to this operation's location");
    }},
    {
        trigger: 'button.o_notification_close',
        run: "click",
    },
    // Scans the right location now.
    { trigger: '.o_barcode_client_action', run: 'scan WH-SECOND-STOCK' },
    { trigger: '.o_scan_message.o_scan_product', run: 'scan product1' },
    { trigger: '.o_barcode_line.o_selected', run: 'scan product1' },
    { trigger: '.o_barcode_line.o_selected', run: 'scan product1' },
    { trigger: '.o_barcode_line.o_selected', run: 'scan product1' },
    ...stepUtils.validateBarcodeOperation('.o_validate_page.btn-primary'),

    // Create a delivery on the fly and try to use both locations as source.
    // Since the delivery is not planned and there is no way for the user to set
    // that from the Barcode app, it should be possible.
    { trigger: ".o_stock_barcode_main_menu", run: 'scan WHOUT' },
    { trigger: '.o_barcode_client_action', run: 'scan WH-SECOND-STOCK' },
    { trigger: '.o_scan_message.o_scan_product', run: 'scan product1' },
    { trigger: '.o_barcode_line', run: 'scan LOC-01-00-00' },
    { trigger: '.o_scan_message.o_scan_validate', run: 'scan product1' },
    {
        trigger: '.o_barcode_location_group + .o_barcode_location_group',
        run: () => {
            helper.assertLinesCount(2);
            helper.assertLineSourceLocation(0, "WH/Second Stock");
            helper.assertLineSourceLocation(1, "WH/Stock");
        }
    },
]});

registry.category("web_tour.tours").add("test_delivery_lot_with_multi_companies", { steps: () => [
    // Scans tsn-002: should find nothing since this SN belongs to another company.
    { trigger: ".o_barcode_client_action", run: "scan tsn-002" },
    // Checks a warning was displayed and scans tsn-001: a line should be added.
    { trigger: ".o_notification_bar.bg-danger", run: "scan tsn-001" },
    {
        trigger: ".o_barcode_line",
        run: function() {
            const line = helper.getLine({ barcode: "productserial1" });
            helper.assert(line.querySelector(".o_line_lot_name").innerText, "tsn-001");
        },
    },
    // Scans tsn-003 then validate the delivery.
    { trigger: ".o_barcode_client_action", run: "scan tsn-003" },
    {
        trigger: ".o_toggle_sublines", // Should have sublines since there is two SN.
    },
    {
        trigger: ".o_validate_page",
        run: "click",
    },
    { trigger: ".o_notification_bar.bg-success"},
]});

registry.category("web_tour.tours").add('test_delivery_lot_with_package', { steps: () => [
    // Unfold grouped lines.
    {
        trigger: '.o_line_button.o_toggle_sublines',
        run: "click",
    },
    {
        trigger: '.o_barcode_client_action:contains("sn2")',
        run: function() {
            helper.assertLinesCount(1);
            helper.assertSublinesCount(2);
            helper.assertScanMessage('scan_serial');
            const [ line1, line2 ] = helper.getSublines();
            helper.assert(line1.querySelector('.o_line_lot_name').innerText, 'sn1');
            helper.assert(line1.querySelector('.fa-archive').parentElement.innerText.includes("pack_sn_1"), true);
            helper.assert(line2.querySelector('.o_line_lot_name').innerText, 'sn2');
            helper.assert(line2.querySelector('.fa-archive').parentElement.innerText.includes("pack_sn_1"), true);
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan productserial1'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn3'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn4'
    },

    {
        trigger: '.o_barcode_client_action:contains("sn4")',
        run: function() {
            helper.assertLinesCount(1);
            helper.assertSublinesCount(4);
            helper.assertScanMessage('scan_validate');
            const [ line1, line2, line3, line4 ] = helper.getSublines();
            helper.assert(line1.querySelector('.o_line_lot_name').innerText, "sn1");
            helper.assert(line1.querySelector('.o_line_owner'), null);
            helper.assert(line1.querySelector('.result-package').innerText, "pack_sn_1");
            helper.assert(line1.querySelector('.package').innerText, "pack_sn_1");
            helper.assert(line2.querySelector('.o_line_lot_name').innerText, "sn3");
            helper.assert(line2.querySelector('.o_line_owner'), null);
            helper.assert(line2.querySelector('.package').innerText, "pack_sn_2");
            helper.assert(line3.querySelector('.o_line_lot_name').innerText, "sn4");
            helper.assert(line3.querySelector('.o_line_owner').innerText, "Particulier");
            helper.assert(line3.querySelector('.package').innerText, "pack_sn_2");
            helper.assert(line4.querySelector('.o_line_lot_name').innerText, "sn2");
            helper.assert(line4.querySelector('.o_line_owner'), null);
            helper.assert(line4.querySelector('.result-package').innerText, "pack_sn_1");
            helper.assert(line4.querySelector('.package').innerText, "pack_sn_1");
        }
    },

    // Open the form view to trigger a save
    {
        trigger: '.o_sublines .o_barcode_line:nth-child(3) .fa-pencil',
        run: "click",
    },
    {
        trigger: '.o_field_widget[name="product_id"]',
        run: function() {
            helper.assertFormQuantity("1");
            helper.assert(document.querySelector('div[name="package_id"] input').value, "pack_sn_2");
            helper.assert(document.querySelector('div[name="result_package_id"] input').value, "");
            helper.assert(document.querySelector('div[name="owner_id"] input').value, "Particulier");
            helper.assert(document.querySelector('div[name="lot_id"] input').value, "sn4");
        },
    },
    {
        trigger: '.o_discard',
        run: "click",
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_delivery_lot_with_package_delivery_step', { steps: () => [
    {
        trigger: '.o_barcode_line',
        run: 'scan LOC-01-02-00',
    },
    {
        trigger: '.o_barcode_line',
        run: 'scan productlot1',
    },
    {
        trigger: '.o_barcode_line',
        run: 'scan sn'
    },
    {
        trigger: '.o_barcode_line:contains("sn")',
        run: 'scan OBTVALI'
    },
    {
        trigger: '.o_notification_bar.bg-success',
        run: function () {
            helper.assertErrorMessage('The transfer has been validated');
        },
    },
]});

registry.category("web_tour.tours").add("test_delivery_pack_from_different_location", {
    steps: () => [
        { trigger: ".o_stock_barcode_main_menu", run: "scan WHOUT" },
        // Scan first source location then scan a product.
        { trigger: ".o_scan_message.o_scan_src", run: "scan LOC-01-01-00" },
        { trigger: ".o_scan_message.o_scan_product", run: "scan product1" },
        // Scan second source location then scan a product.
        { trigger: ".o_barcode_line.o_selected", run: "scan LOC-01-02-00" },
        { trigger: ".o_barcode_line:not(.o_selected)", run: "scan product1" },
        {
            content: "Check lines source location before to scan the package.",
            trigger: ".o_barcode_line:nth-child(2).o_selected",
            run: () => {
                helper.assertLinesCount(2);
                helper.assertLineSourceLocation(0, "WH/Stock/Section 1");
                helper.assertLineSourceLocation(1, "WH/Stock/Section 2");
            }
        },
        // Scan an empty package and check the lines' source weren't changed.
        { trigger: ".o_barcode_line.o_selected", run: "scan pack-test" },
        {
            trigger: ".o_barcode_line .result-package",
            run: () => {
                helper.assertLinesCount(2);
                const [ line1, line2 ] = helper.getLines();
                helper.assertLineSourceLocation(line1, "WH/Stock/Section 1");
                helper.assert(line1.querySelector('.result-package').innerText, "pack-test");
                helper.assertLineSourceLocation(line2, "WH/Stock/Section 2");
                helper.assert(line2.querySelector('.result-package').innerText, "pack-test");
            }
        },
    ],
});

registry.category("web_tour.tours").add('test_delivery_reserved_1', { steps: () => [
    // test that picking note properly pops up + close it
    {
        trigger: '.alert:contains("A Test Note")',
        run: "click",
    },
    {
        trigger: '.alert button.btn-close',
        run: "click",
    },
    // Opens and close the line's form view to be sure the note is still hidden.
    {
        trigger: '.o_add_line',
        run: "click",
    },
    {
        trigger: '.o_discard',
        run: "click",
    },
    {
        trigger: '.o_barcode_lines',
        run: function() {
            const note = document.querySelector('.alert.alert-warning');
            helper.assert(Boolean(note), false, "Note must not be present");
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(2);
            helper.assertScanMessage('scan_src');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-00-00'
    },

    {
        trigger: '.o_scan_message.o_scan_product',
        run: function() {
            helper.assertLinesCount(2);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.o_barcode_line:nth-child(2).o_selected',
        run: 'scan product2'
    },
    { trigger: '.o_barcode_line:nth-child(3).o_selected' },

    // Display the picking's information to trigger a save.
    {
        trigger: '.o_barcode_header .o_title',
        run: "click",
    },
    {
        trigger: '.o_barcode_control .btn.o_discard',
        run: "click",
    },
    { trigger: '.o_barcode_line' },
]});

registry.category("web_tour.tours").add('test_delivery_reserved_2', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(2);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: 'scan product2'
    },
    ...stepUtils.confirmAddingUnreservedProduct(),

    {
        trigger: '.o_barcode_line.o_selected:contains("product2")',
        run: function() {
            helper.assertLinesCount(3);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
            const p1_lines = helper.getLines({ barcode: 'product1' });
            helper.assertLineIsFaulty(p1_lines[0], false);
            helper.assertLineIsFaulty(p1_lines[1], false);
            const p2_line = helper.getLine({ barcode: 'product2' });
            helper.assertLineIsFaulty(p2_line, true);
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.o_barcode_line.o_selected:not(.o_line_completed)',
        run: 'scan product1'
    },

    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: function() {
            helper.assertLinesCount(3);
            helper.assertScanMessage('scan_validate');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(true);
            helper.assertValidateEnabled(true);
            const lines = helper.getLines({ barcode: 'product1' });
            [0, 1].map(i => helper.assertLineQty(lines[i], "2/2"));
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.o_barcode_line:nth-child(4)',
        run: function () {
            helper.assertLinesCount(4);
            helper.assertScanMessage('scan_validate');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(true);
            helper.assertValidateEnabled(true);
            const p1_lines = helper.getLines({ barcode: 'product1' });
            helper.assertLineIsFaulty(p1_lines[0], false);
            helper.assertLineIsFaulty(p1_lines[1], false);
            helper.assertLineIsFaulty(p1_lines[2], true);
            const p2_line = helper.getLine({ barcode: 'product2' });
            helper.assertLineIsFaulty(p2_line, true);
        }
    },
]});

registry.category("web_tour.tours").add('test_delivery_reserved_3', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(1);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
        }
    },
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    { trigger: '.o_barcode_client_action', run: 'scan this_is_not_a_barcode_dude' },
    {
        trigger: '.o_barcode_line.o_highlight',
        run: function() {
            helper.assertLinesCount(1);
            helper.assertScanMessage('scan_validate');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(true);
            helper.assertValidateEnabled(true);
            helper.assertLineIsHighlighted(0, true);
            helper.assertLineQty(0, "1/1");
        }
    },
]});

registry.category("web_tour.tours").add("test_delivery_reserved_4_backorder", {  steps: () => [
    {
        trigger: ".o_barcode_client_action",
        run: function() {
            // The picking has 3 moves but only 2 barcode lines because the move for product3
            // has no reservation, so no move line, so no barcode line neither.
            helper.assertLinesCount(2);
            helper.assertLineQty(0, "0/4"); // 4 demand, 4 reserved.
            helper.assertLineQty(1, "0/2"); // 4 demand but only 2 reserved.
        }
    },
    // Scans product1 then tries to validate again -> Should display the backorder dialog.
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    {
        trigger: ".o_barcode_line.o_selected",
    },
    {
        trigger: ".o_validate_page",
        run: "click",
    },
    {
        trigger: ".modal-content.o_barcode_backorder_dialog",
        run: function() {
            const incompleteLines = document.querySelectorAll(".o_barcode_backorder_product_row");
            helper.assert(incompleteLines.length, 2);
            const [line1, line2] = incompleteLines;
            helper.assert(line1.querySelector("[name='qty-done']").innerText, "1");
            helper.assert(line1.querySelector("[name='reserved-qty']").innerText, "4");
            helper.assert(line1.querySelector("[name='backorder-qty']").innerText, "3");
            helper.assert(line2.querySelector("[name='qty-done']").innerText, "0");
            helper.assert(line2.querySelector("[name='reserved-qty']").innerText, "2");
            helper.assert(line2.querySelector("[name='backorder-qty']").innerText, "2");
        },
    },
    {
        trigger: ".modal-dialog button.btn-secondary",
        run: "click",
    }, // Cancel -> Stay on the delivery.
    // Scans 3 more times product1 to complete the line then clicks on validate again.
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    {
        trigger: ".o_barcode_line.o_selected.o_line_completed",
    },
    {
        trigger: ".o_validate_page",
        run: "click",
    },
    {
        trigger: ".modal-content.o_barcode_backorder_dialog",
        run: function() {
            const incompleteLines = document.querySelectorAll(".o_barcode_backorder_product_row");
            helper.assert(incompleteLines.length, 1);
            const [incompleteLine] = incompleteLines;
            helper.assert(incompleteLine.querySelector("[name='qty-done']").innerText, "0");
            helper.assert(incompleteLine.querySelector("[name='reserved-qty']").innerText, "2");
            helper.assert(incompleteLine.querySelector("[name='backorder-qty']").innerText, "2");
        },
    },
    {
        trigger: ".modal-dialog button.btn-primary",
        run: "click",
    }, // Validate -> Should create a backorder.
    {
        trigger: ".o_notification",
        run: function() {
            const backorderLink = document.querySelector(".o_notification_buttons span");
            helper.assert(
                backorderLink.innerText.includes("WH/OUT/"), true,
                "The notification should contain a link to the created backorder."
            );
        },
    }
]});

registry.category("web_tour.tours").add("test_delivery_reserved_5_dont_show_reserved_sn", {  steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertScanMessage('scan_product');
            helper.assertLinesCount(1);
            helper.assertLineQty(0, "0/4");
            helper.assertLineProduct(0, "productserial1");
            helper.assertLineTrackingNumber(0, "");
            helper.assertButtonIsVisible(0, "toggle_sublines", false);
            helper.assertButtonIsVisible(0, "edit");
        }
    },
    { trigger: '.o_barcode_client_action', run: 'scan productserial1' },
    // Increases qty via the form view. Since it's a move line form view, a SN is already set.
    { trigger: '.o_barcode_line.o_selected .btn.o_edit', run: "click" },
    {
        trigger: ".o_form_view_container",
        run: () => {
            const lotField = document.querySelector('.o_field_widget[name="lot_id"] input');
            helper.assert(lotField.value, "sn1", "Should display move line for sn1");
        }
    },
    { trigger: '.o_field_widget[name=qty_done] input', run: "clear" },
    { trigger: '.o_field_widget[name=qty_done] input', run: "edit 1" },
    { trigger: '.o_save', run: "click" },
    // Now there is at least 1 qty for a specific SN, this SN should be visible.
    {
        trigger: '.o_barcode_line',
        run: () => {
            helper.assertScanMessage('scan_serial');
            helper.assertLinesCount(1);
            helper.assertLineQty(0, "1/4");
            helper.assertLineTrackingNumber(0, "sn1");
            helper.assertButtonIsVisible(0, "toggle_sublines", false);
        }
    },
    // Opens it again to checks it still the same move line who is displayed.
    { trigger: '.o_barcode_line.o_selected .btn.o_edit', run: "click" },
    {
        trigger: ".o_form_view_container",
        run: () => {
            const lotField = document.querySelector('.o_field_widget[name="lot_id"] input');
            helper.assert(lotField.value, "sn1", "Should still display move line for sn1");
        }
    },
    { trigger: '.o_discard', run: "click" },

    // Scans sn5 (not reserved). As soon there is at least two scanned SN,
    // the button to display sublines should be visible.
    { trigger: '.o_barcode_client_action', run: 'scan sn5' },
    {
        trigger: '.o_line_button.o_toggle_sublines',
        run: function() {
            helper.assertLineQty(0, "2/4");
        }
    },

    // "There should be no faulty line if show reserved sn/lot is disabled"
    { trigger: '.o_line_button.o_toggle_sublines', run: 'click' },
    {
        trigger: '.o_sublines',
        run: function() {
            helper.assertLineQty(0, "2/4");
            const unreservedLine = document.querySelector('.o_faulty');
            helper.assert(
                Boolean(unreservedLine), false, "There should be no faulty line if show reserved sn/lot is disabled"
            );
        }
    },

    // Scans 2 more SN to complete the delivery and validates it.
    { trigger: '.o_barcode_client_action', run: 'scan sn2' },
    { trigger: '.o_barcode_client_action', run: 'scan sn3' },
    ...stepUtils.validateBarcodeOperation(".o_barcode_line.o_selected.o_line_completed"),
]});

registry.category("web_tour.tours").add("test_delivery_reserved_6_dont_show_reserved_lots", {  steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertScanMessage('scan_product');
            helper.assertLinesCount(1);
            helper.assertLineQty(0, "0/12");
            helper.assertLineProduct(0, "productlot1");
            helper.assertButtonIsVisible(0, "toggle_sublines", false);
            helper.assertButtonIsVisible(0, "edit");
            helper.assertLineTrackingNumber(0, "");
        }
    },
    { trigger: '.o_barcode_client_action', run: 'scan productlot1' },
    {
        trigger: '.o_barcode_line.o_selected',
        run: function() {
            helper.assertScanMessage('scan_lot');
            helper.assertLinesCount(1);
            helper.assertLineQty(0, "0/12");
            helper.assertLineProduct(0, "productlot1");
            helper.assertButtonIsVisible(0, "toggle_sublines", false);
            helper.assertButtonIsVisible(0, "edit");
            helper.assertLineTrackingNumber(0, "");
        }
    },
    { trigger: '.o_barcode_client_action', run: 'scan lot-001' },
    {
        trigger: '.o_line_lot_name:contains("lot")',
        run: function() {
            helper.assertScanMessage('scan_lot');
            helper.assertLinesCount(1);
            helper.assertLineQty(0, "1/12");
            helper.assertLineProduct(0, "productlot1");
            helper.assertButtonIsVisible(0, "toggle_sublines", false);
            helper.assertButtonIsVisible(0, "edit");
            helper.assertLineTrackingNumber(0, "lot-001");
        }
    },
    // Scan a second lot, the scanned lots should be visible in sublines.
    { trigger: '.o_barcode_client_action', run: 'scan lot-002' },
    {
        trigger: '.o_line_button.o_toggle_sublines',
        run: function() {
            helper.assertScanMessage('scan_lot');
            helper.assertLinesCount(1);
            helper.assertLineQty(0, "2/12");
            helper.assertLineProduct(0, "productlot1");
            helper.assertButtonIsVisible(0, "toggle_sublines");
            helper.assertButtonIsVisible(0, "edit", false);
            helper.assertLineTrackingNumber(0, false);
        }
    },
    // Display sublines.
    { trigger: '.o_line_button.o_toggle_sublines', run: "click" },
    {
        trigger: '.o_sublines .o_barcode_line',
        run: function() {
            const sublines = helper.getSublines();
            helper.assertLinesCount(1);
            helper.assertSublinesCount(2);
            helper.assertLineQty(sublines[0], "1");
            helper.assertLineQty(sublines[1], "1");
            helper.assertLinesTrackingNumbers(sublines, ["lot-001", "lot-002"]);
        }
    },
    // Scan unreserved lot (lot-005).
    { trigger: '.o_barcode_client_action', run: 'scan lot-005' },
    {
        trigger: '.o_sublines .o_barcode_line:nth-child(3)',
        run: function() {
            const sublines = helper.getSublines();
            helper.assertLinesCount(1);
            helper.assertSublinesCount(3);
            helper.assertLineQty(sublines[0], "1");
            helper.assertLineQty(sublines[1], "1");
            helper.assertLineQty(sublines[2], "1");
            helper.assertLinesTrackingNumbers(sublines, ["lot-001", "lot-002", "lot-005"]);
        }
    },
]});

registry.category("web_tour.tours").add('test_delivery_using_buttons', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(3);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
            helper.assertLineQty(0, "0/2");
            helper.assertLineQty(1, "0/3");
            helper.assertLineQty(2, "0/4");
            helper.assertButtonIsVisible(0, "add_quantity", false);
            helper.assertButtonIsVisible(1, "add_quantity", false);
            helper.assertButtonIsVisible(2, "add_quantity", false);
            helper.assertButtonIsVisible(0, "add_remaining_quantity");
            helper.assertButtonIsVisible(1, "add_remaining_quantity");
            helper.assertButtonIsVisible(2, "add_remaining_quantity");
        }
    },

    // On the first line, goes on the form view and press digipad +1 button.
    {
        trigger: '.o_barcode_line:first-child .o_edit',
        run: "click",
    },
    {
        trigger: 'button.o_digipad_increment',
        run: "click",
    },
    {
        trigger: '.o_save',
        run: "click",
    },
    {
        trigger: '.o_barcode_lines',
        run: function() {
            helper.assertButtonIsVisible(0, "remove_unit");
            helper.assertButtonIsVisible(0, "add_quantity", false);
            helper.assertButtonIsVisible(0, "add_remaining_quantity");
            helper.assertLineQty(0, '1/2');
            helper.assertLineIsHighlighted(0, true);
            helper.assertLineIsHighlighted(1, false);
            helper.assertLineIsHighlighted(2, false);
        }
    },
    // Press +1 button again, now its buttons must be hidden.
    {
        trigger: '.o_barcode_line:first-child .o_add_remaining_quantity',
        run: "click",
    },
    {
        trigger: '.o_barcode_line:first-child.o_selected.o_line_completed',
        run: function() {
            helper.assertLineQty(0, '2/2');
            helper.assertButtonIsVisible(0, "remove_unit");
            helper.assertButtonIsVisible(0, "add_quantity", false);
            helper.assertButtonIsVisible(0, "add_remaining_quantity", false);
            helper.assertLineQty(1, '0/3');
            helper.assertButtonIsVisible(1, "add_quantity", false);
            helper.assertButtonIsVisible(1, "add_remaining_quantity");
        }
    },
    // Press the add remaining quantity button.
    {
        trigger: '.o_barcode_line:nth-child(2) .o_add_remaining_quantity',
        run: "click",
    },
    // Product2 is now done, its button must be hidden.
    {
        trigger: '.o_barcode_line:nth-child(2).o_selected.o_line_completed',
        run: function() {
            helper.assertLineIsHighlighted(0, false);
            helper.assertLineIsHighlighted(1, true);
            helper.assertLineIsHighlighted(2, false);
            helper.assertLineQty(1, '3/3');
            helper.assertButtonIsVisible(1, "remove_unit");
            helper.assertButtonIsVisible(1, "add_quantity", false);
            helper.assertButtonIsVisible(1, "add_remaining_quantity", false);
            helper.assertLineQty(2, "0/4");
            helper.assertButtonIsVisible(2, "add_quantity", false);
            helper.assertButtonIsVisible(2, "add_remaining_quantity");
        }
    },
    // Scan product3 one time, then checks the quantities.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product3',
    },
    {
        trigger: '.o_barcode_line:last-child.o_selected .qty-done:contains("1")',
        run: function() {
            helper.assertLineQty(2, "1/4");
            helper.assertButtonIsVisible(2, "add_quantity");
            helper.assertButtonIsVisible(2, "add_remaining_quantity");
            helper.assertLineIsHighlighted(0, false);
            helper.assertLineIsHighlighted(1, false);
            helper.assertLineIsHighlighted(2, true);
        }
    },
    // Goes on the form view and press digipad +1 button.
    {
        trigger: '.o_barcode_line:last-child .o_edit',
        run: "click",
    },
    {
        trigger: 'button.o_digipad_increment',
        run: "click",
    },
    {
        trigger: '.o_save',
        run: "click",
    },
    {
        trigger: '.o_barcode_lines',
        run: function() {
            helper.assertLineQty(0, "2/4");
            helper.assertButtonIsVisible(0, "add_quantity");
            helper.assertButtonIsVisible(0, "add_remaining_quantity");
        }
    },
    // Press the add remaining quantity button, then the button must be hidden.
    {
        trigger: '.o_barcode_line:first-child .o_add_remaining_quantity',
        run: "click",
    },
    {
        trigger: '.o_barcode_line:first-child .qty-done:contains("4")',
        run: function() {
            helper.assertLineQty(0, "4/4");
            helper.assertButtonIsVisible(0, "add_quantity", false);
            helper.assertButtonIsVisible(0, "add_remaining_quantity", false);
            helper.assertValidateIsHighlighted(true);
        }
    },

    // Now, scan one more time the product3 to create a new line (its +1 button must be visible).
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product3',
    },
    // The new line is created at the second position (directly below the previous selected line).
    {
        trigger: '.o_barcode_line:nth-child(2).o_selected',
        run: function() {
            helper.assertLinesCount(4);
            helper.assertLineIsHighlighted(0, false);
            helper.assertLineIsHighlighted(1, true);
            helper.assertLineIsHighlighted(2, false);
            helper.assertLineIsHighlighted(3, false);
            helper.assertLineQty(1, "1");
            // +1 button must be present on new line.
            helper.assertButtonIsVisible(1, "remove_unit");
            helper.assertButtonIsVisible(1, "add_quantity");
            helper.assertButtonIsVisible(1, "add_remaining_quantity", false);
            helper.assertButtonIsVisible(1, "delete_line");
        }
    },
    // Press +1 button of the new line.
    {
        trigger: '.o_barcode_line:nth-child(2) .o_add_quantity',
        run: "click",
    },
    {
        trigger: '.o_barcode_line:nth-child(2) .qty-done:contains("2")',
        run: function() {
            helper.assertLineIsHighlighted(0, false);
            helper.assertLineIsHighlighted(1, true);
            helper.assertLineIsHighlighted(2, false);
            helper.assertLineIsHighlighted(3, false);
            helper.assertLineQty(1, '2');
            // +1 button must still be present.
            helper.assertButtonIsVisible(1, 'add_quantity');
        }
    },

    // Validate the delivery.
    {
        trigger: '.o_validate_page',
        run: "click",
    },
    {
        trigger: '.o_notification_bar.bg-success',
    },
]});

registry.category("web_tour.tours").add('test_remaining_decimal_accuracy', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
            helper.assertLineQty(0, "0/4");
            helper.assertLineQty(1, "0/0.12");
            helper.assertLineQty(2, "0/4");
            helper.assertButtonIsVisible(0, "add_remaining_quantity");
            helper.assertButtonIsVisible(1, "add_remaining_quantity");
        }
    },

    // Goes on the first line form view and add 2.2 .
    {
        trigger: '.o_barcode_line[data-barcode="product1"] .o_edit',
        run: "click",
    },
    {
        trigger: 'div[name=qty_done] input',
        run() {
            //input type number not supported by tour helpers.
            // It would work if the clipboard was mocked in tours the same way it is in unit tests.
            this.anchor.value = "2.2";
            this.anchor.dispatchEvent(new InputEvent("input", { bubbles: true }));
        }
    },
    {
        trigger: '.o_save',
        run: "click",
    },
    {
        trigger: '.o_barcode_lines',
        run: function() {
            helper.assertButtonIsVisible(0, "add_remaining_quantity");
            helper.assertLineQty(0, '2.2/4');
            const buttonAddQty = document.querySelector(".o_barcode_line:first-child .o_add_remaining_quantity");
            helper.assert(buttonAddQty.innerText, "+1.8", "Something wrong with the quantities");
        }
    },
    // Adds 0.12 (entire demand, less than 1) of the second product
    {
        trigger: '.o_barcode_line:last-child .o_add_remaining_quantity:contains("0.12")',
        run: "click",
    },
    {
        trigger: '.o_barcode_lines',
        run: function() {
            helper.assertButtonIsVisible(1, 'add_remaining_quantity', false);
            helper.assertLineQty(1, '0.12/0.12');
        }
    },

    // test qty buttons are correct for grouped lines
    {
        trigger: '.o_line_button.o_toggle_sublines',
        run: "click",
    },
    // Go on the form view and update the lot1 with 2.345 .
    {
        trigger: '.o_sublines .o_barcode_line:first-child .fa-pencil',
        run: "click",
    },
    {
        trigger: 'div[name=qty_done] input',
        run() {
            this.anchor.value = "2.345";
        }
    },
    {
        trigger: '.o_save',
        run: "click",
    },
    // Check the lot2 qty button display "+1.65"
    {
        trigger: '.o_sublines .o_barcode_line:first-child',
        run: function() {
            const buttonAddQty = document.querySelector(".o_sublines .o_barcode_line:first-child .o_add_remaining_quantity");
            helper.assert(buttonAddQty.innerText, "+1.65", "Something wrong with the quantities");
        }
    },
]});

registry.category("web_tour.tours").add('test_receipt_from_scratch_with_lots_1', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.o_notification_bar.bg-danger',
        run: "click",
    },

    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertErrorMessage("This product doesn't exist.");
        },
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan productserial1'
    },

    {
        trigger: '.o_barcode_line',
        run: 'scan lot1',
    },

    {
        trigger: '.o_line_lot_name:contains("lot1")',
        run: 'scan LOC-01-00-00'
    },

    {
        trigger: '.o_scan_message.o_scan_validate',
        run: 'scan productserial1'
    },
    {
        trigger: '.o_barcode_line.o_selected .btn.o_toggle_sublines .fa-angle-down',
        run: "click",
    },

    {
        trigger: '.o_barcode_line:nth-child(2)',
        run: 'scan lot2',
    },

    {
        trigger: '.o_line_lot_name:contains("lot2")',
        run: 'scan LOC-01-01-00'
    },

    { trigger: '.o_scan_message.o_scan_validate', run: 'scan productserial1' },
    { trigger: '.o_scan_message.o_scan_serial', run: 'scan lot3' },
    { trigger: '.o_scan_message.o_scan_product_or_dest', run: 'scan WHSTOCK-2' },
    {
        trigger: '.o_scan_message.o_scan_validate',
        run: () => {
            helper.assertLinesCount(3);
            helper.assertLineDestinationLocation(0, "WH/Stock");
            helper.assertLineDestinationLocation(1, ".../Section 1");
            helper.assertLineDestinationLocation(2, "WH/Stock 2");
        }
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_receipt_from_scratch_with_lots_2', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan productlot1'
    },

    {
        trigger: '.o_barcode_line .o_edit',
        run: "click",
    },

    {
        trigger: '.o_input[id=lot_id_0]',
        run: function () {
            // Check if the lot_name is invisible
            helper.assert(document.querySelectorAll('#lot_name_0').length, 0);
        }
    },

    {
        trigger: '.o_save',
        run: "click",
    },

    {
        trigger: '.o_barcode_line',
        run: 'scan lot1',
    },

    {
        trigger: '.o_line_lot_name:contains(lot1)',
        run: "click",
    },

    {
        trigger: '.o_barcode_line .o_edit',
        run: "click",
    },

    {
        trigger: '.o_input[id="lot_name_0"]',
        run: function () {
            // check that the lot_id is invisible
            helper.assert(document.querySelectorAll('#lot_id_0').length, 0);
         }
    },

    {
        trigger: '.o_save',
        run: "click",
    },

    {
        trigger: '.o_line_lot_name:contains(lot1)',
        run: 'scan lot1',
    },

    {
        trigger: '.qty-done:contains(2)',
        run: 'scan lot2',
    },
    {
        trigger: '.o_barcode_line.o_selected .btn.o_toggle_sublines .fa-angle-down',
        run: "click",
    },

    {
        trigger: '.o_barcode_line:nth-child(2)',
        run: 'scan lot2',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-01-00'
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_receipt_from_scratch_with_lots_3', { steps: () => [
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    {
        trigger: '.o_barcode_line',
        run: function() {
            helper.assertLinesCount(1);
            const line = helper.getLine({barcode: 'product1'});
            helper.assertLineIsHighlighted(line, true);
            helper.assertLineQty(line, "1");
        }
    },

    // Scans a second time product1 after going through the edit form view.
    {
        trigger: '.o_barcode_line.o_selected .btn.o_edit',
        run: "click",
    },
    {
        trigger: '.o_discard',
        run: "click",
    },
    { trigger: '.o_barcode_client_action', run: 'scan product1' },

    {
        trigger: '.o_barcode_line .qty-done:contains("2")',
        run: 'scan productlot1'
    },

    {
        trigger: '.o_barcode_line:nth-child(2)',
        run: function() {
            helper.assertLinesCount(2);
            const line1 = helper.getLine({ barcode: 'product1' });
            const line2 = helper.getLine({ barcode: 'productlot1' });
            helper.assertLineIsHighlighted(line1, false);
            helper.assertLineQty(line1, "2");
            helper.assertLineIsHighlighted(line2, true);
            helper.assertLineQty(line2, "0");
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.o_selected .qty-done:contains(2)',
        run: function() {
            helper.assertLinesCount(2);
            const line1 = helper.getLine({ barcode: 'product1' });
            const line2 = helper.getLine({ barcode: 'productlot1' });
            helper.assertLineIsHighlighted(line1, false);
            helper.assertLineQty(line1, "2");
            helper.assertLineIsHighlighted(line2, true);
            helper.assertLineQty(line2, "2");
        }
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_receipt_from_scratch_with_lots_4', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan productserial1',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan productserial1',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan productserial1',
    },
    {
        trigger: '.qty-done:contains("3")',
    },
    {
        trigger: '.o_add_line',
        run: "click",
    },
    {
        trigger: '.o_field_widget[name="product_id"]',
        run: "click",
    },
    ...stepUtils.discardBarcodeForm(),
]});

registry.category("web_tour.tours").add('test_delivery_from_scratch_with_lots_1', { steps: () => [

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot2',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot2',
    },
    // Open the form view to trigger a save
    {
        trigger: '.o_barcode_line.o_selected .btn.o_toggle_sublines .fa-angle-down',
        run: "click",
    },
    {
        trigger: '.o_barcode_line:nth-child(2)',
    },
    {
        trigger: '.o_add_line',
        run: "click",
    },

    {
        trigger: '.o_field_widget[name="product_id"]',
        run: "click",
    },
    ...stepUtils.discardBarcodeForm(),
]});

registry.category("web_tour.tours").add('test_delivery_from_scratch_with_incompatible_lot', { steps: () => [
    { trigger: '.o_barcode_client_action', run: 'scan 0000000001' },
    {
        trigger: '.o_barcode_line:first-child .o_edit',
        run: "click",
    },
    ...stepUtils.discardBarcodeForm(),
]});

registry.category("web_tour.tours").add('test_delivery_from_scratch_with_common_lots_name', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1',
    },
    {
        trigger: '.o_barcode_line',
        run: 'scan LOT01',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOT01',
    },
    {
        trigger: '.o_barcode_line[data-barcode="product1"] .qty-done:contains("2")',
        run: 'scan product2',
    },
    {
        trigger: '.o_barcode_line:contains("product2")',
        run: 'scan LOT01',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOT01',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOT01',
    },
    {
        trigger: '.qty-done:contains("3")',
        run: 'scan SUPERSN',
    },
    {
        trigger: '.o_barcode_line:contains("productserial1")',
        run: "click",
    },
    // Open the form view to trigger a save
    {
        trigger: '.o_barcode_line:first-child .o_edit',
        run: "click",
    },
    ...stepUtils.discardBarcodeForm(),
]});

registry.category("web_tour.tours").add('test_receipt_with_sn_1', { steps: () => [
    { trigger: '.o_barcode_client_action', run: 'scan sn1' },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_delivery_from_scratch_with_sn_1', { steps: () => [
    /* scan a product tracked by serial number. Then scan 4 a its serial numbers.
    */
    {
        trigger: '.o_barcode_client_action',
        run: 'scan productserial1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn1',
    },

    {
        trigger: '.o_notification_bar.bg-danger',
        run: function () {
            helper.assertErrorMessage('The scanned serial number sn1 is already used.');
        },
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn2',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn3',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn4',
    },
    // Open the form view to trigger a save
    {
        trigger: '.o_add_line',
        run: "click",
    },

    {
        trigger: '.o_field_widget[name="product_id"]',
        run: "click",
    },

]});

registry.category("web_tour.tours").add('test_delivery_reserved_lots_1', { steps: () => [
    { trigger: '.o_barcode_client_action', run: 'scan productlot1' },
    { trigger: '.o_barcode_line.o_selected .o_toggle_sublines', run: 'click' },
    {
        trigger: '.o_sublines',
        run: function() {
            helper.assertLinesCount(1);
            helper.assertSublinesCount(2);
            const sublines = helper.getSublines();
            helper.assertLineQty(sublines[0], "0/2");
            helper.assert(sublines[0].querySelector('button.o_add_remaining_quantity').innerText, "+2");
            helper.assertLineQty(sublines[1], "0/3");
            helper.assert(sublines[1].querySelector('button.o_add_remaining_quantity').innerText, "+3");
        },
    },
    { trigger: '.o_barcode_client_action', run: 'scan lot1' },
    { trigger: '.o_barcode_line.o_selected', run: 'scan lot2' },
    { trigger: '.o_barcode_line.o_selected', run: 'scan lot3' },
    {
        trigger: '.o_sublines .o_barcode_line:nth-child(3)',
        run: function() {
            helper.assertLinesCount(1);
            helper.assertSublinesCount(3);
            const sublines = helper.getSublines();
            // Check lines and "Add quantity" buttons quantities are correctly updated.
            helper.assertLineQty(sublines[0], "1/2");
            helper.assert(sublines[0].querySelector('button.o_add_remaining_quantity').innerText, "+1");
            helper.assertLineQty(sublines[1], "1/3");
            helper.assert(sublines[1].querySelector('button.o_add_remaining_quantity').innerText, "+2");
            helper.assertLineQty(sublines[2], "1");
            helper.assert(sublines[2].querySelector('button.o_add_remaining_quantity').innerText, "+1");

        },
    },
    { trigger: '.o_barcode_client_action', run: 'scan lot1' },
    {
        trigger: '.o_sublines .o_barcode_line.o_selected.o_line_completed',
        run: function() {
            helper.assertLinesCount(1);
            helper.assertSublinesCount(3);
            const sublines = helper.getSublines();
            helper.assertLineQty(sublines[0], "2/2");
            helper.assert(sublines[0].querySelector('button.o_add_remaining_quantity').innerText, "+1");
            helper.assertLineQty(sublines[1], "1/3");
            helper.assert(sublines[1].querySelector('button.o_add_remaining_quantity').innerText, "+1");
            helper.assertLineQty(sublines[2], "1");
            helper.assert(sublines[2].querySelector('button.o_add_remaining_quantity').innerText, "+1");
        },
    },
    { trigger: '.o_barcode_line.o_selected:not(.o_line_completed)', run: 'scan lot2' },
    {
        trigger: '.o_barcode_location_group > .o_barcode_line.o_line_completed',
        run: function() {
            helper.assertLinesCount(1);
            helper.assertSublinesCount(3);
            const sublines = helper.getSublines();
            // Since the reservation is completed, no "Add Quantity" buttons should be displayed.
            helper.assertLineQty(sublines[0], "2/2");
            helper.assertButtonIsVisible(sublines[0], "add_quantity", false);
            helper.assertButtonIsVisible(sublines[0], "o_add_remaining_quantity", false);
            helper.assertLineQty(sublines[1], "2/3");
            helper.assertButtonIsVisible(sublines[1], "add_quantity", false);
            helper.assertButtonIsVisible(sublines[1], "o_add_remaining_quantity", false);
            helper.assertLineQty(sublines[2], "1");
            helper.assertButtonIsVisible(sublines[2], "add_quantity", false);
            helper.assertButtonIsVisible(sublines[2], "o_add_remaining_quantity", false);
        },
    },
    // Open the form view to trigger a save.
    { trigger: '.o_add_line', run: "click" },
    { trigger: '.o_field_widget[name="product_id"]' },
    ...stepUtils.discardBarcodeForm(),
]});

registry.category("web_tour.tours").add('test_delivery_different_products_with_same_lot_name', { steps: () => [

    {
        trigger: '.o_barcode_client_action',
        run: 'scan productlot1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.o_barcode_line:has(.o_product_label:contains(productlot1)) .qty-done:contains(2)',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan productlot2',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.o_barcode_line:has(.o_product_label:contains(productlot2)) .qty-done:contains(2)',
    },
    // Open the form view to trigger a save
    {
        trigger: '.o_add_line',
        run: "click",
    },

    {
        trigger: '.o_field_widget[name="product_id"]',
        run: "click",
    },
    ...stepUtils.discardBarcodeForm(),
]});

registry.category("web_tour.tours").add('test_delivery_reserved_with_sn_1', { steps: () => [
    /* scan a product tracked by serial number. Then scan 4 a its serial numbers.
    */
    { trigger: '.o_barcode_client_action', run: 'scan productserial1' },
    { trigger: '.o_barcode_line.o_selected', run: 'scan sn3' },
    { trigger: '.o_barcode_client_action', run: 'scan sn3' },
    {
        trigger: '.o_notification_bar.bg-danger',
        run: function () {
            helper.assertErrorMessage('The scanned serial number sn3 is already used.');
        },
    },

    { trigger: '.o_barcode_client_action', run: 'scan sn1' },
    { trigger: '.o_barcode_client_action', run: 'scan sn4' },
    { trigger: '.o_barcode_client_action', run: 'scan sn2' },
    { trigger: '.o_barcode_line .qty-done:contains("4")' },
    // Open the form view to trigger a save
    { trigger: '.o_add_line', run: "click" },
    {
        trigger: '.o_field_widget[name="product_id"]',
        run: "click",
    },
    ...stepUtils.discardBarcodeForm(),
]});

registry.category("web_tour.tours").add('test_nomenclature_alias_and_conversion', { steps: () => [
    // Before all, create a new receipt on the fly.
    { trigger: '.o_stock_barcode_main_menu', run: 'scan WHIN' },
    // First, scan the alias and check the product was found (a line was then created.)
    { trigger: '.o_barcode_client_action', run: 'scan alias_for_upca' },
    {
        trigger: '.o_barcode_line.o_selected',
        run: function () {
            const line = helper.getLine({ barcode: '123123123125' });
            helper.assertLineQty(line, "1");
        }
    },
    // Secondly, scan the product's barcode but as a EAN-13.
    { trigger: '.o_barcode_line.o_selected .qty-done:contains(1)', run: 'scan 0123123123125' },

    // Then scan the second alias (who will be replaced by an EAN-13) and check the product is find
    // in that case too (the EAN-13 should be converted into a UPC-A even if it comes from an alias,
    // that's where the rules order is important since the alias rule should be used before the rule
    // who convert an EAN-13 into an UPC-A).
    { trigger: '.o_barcode_line.o_selected .qty-done:contains(2)', run: 'scan alias_for_ean13' },

    // Finally, checks we can still scan the raw product's barcode :)
    { trigger: '.o_barcode_line.o_selected .qty-done:contains(3)', run: 'scan 123123123125' },
    {
        trigger: '.o_barcode_line.o_selected .qty-done:contains(4)',
        run: function () {
            const line = helper.getLine({ barcode: '123123123125' });
            helper.assertLineQty(line, "4");
        }
    },
]});

registry.category("web_tour.tours").add('test_receipt_reserved_lots_multiloc_1', { steps: () => [
    /* Receipt of a product tracked by lots. Open an existing picking with 4
    * units initial demands. Scan 2 units in lot1 in location WH/Stock. Then scan
    * 2 unit in lot2 in location WH/Stock/Section 2
    */

    {
        trigger: '.o_barcode_client_action',
        run: 'scan productlot1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.o_barcode_line .qty-done:contains("2")',
        run: 'scan LOC-01-02-00',
    },

    {
        trigger: '.o_barcode_line .o_line_destination_location:contains("Section 2")',
        run: 'scan productlot1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot2',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot2',
    },

    {
        trigger: '.o_barcode_line.o_selected:contains("lot2") .qty-done:contains("2")',
        run: 'scan LOC-01-01-00',
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_receipt_duplicate_serial_number', { steps: () => [
    // Create a receipt. Try to scan twice the same serial in different locations.
    { trigger: '.o_stock_barcode_main_menu:contains("Scan or tap")', run: "click" },
    { trigger: '.o_stock_barcode_main_menu', run: 'scan WHIN' },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan productserial1',
    },

    {
        trigger: '.o_barcode_line',
        run: 'scan sn1',
    },

    {
        trigger: '.o_barcode_line .o_line_lot_name:contains("sn1")',
        run: 'scan LOC-01-01-00',
    },

    {
        trigger: '.o_barcode_line .o_line_destination_location:contains("../Section 1")',
        run: 'scan productserial1',
    },

    {
        trigger: '.o_barcode_line:nth-child(2)',
        run: 'scan sn1',
    },

    {
        trigger: '.o_notification_bar.bg-danger',
        run: function () {
            helper.assertErrorMessage('The scanned serial number sn1 is already used.');
        },
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn2',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-02-00',
    },
    {
        trigger: '.o_barcode_line:nth-child(2) .o_line_destination_location:contains("../Section 2")',
        run: 'scan OBTVALI'
    },
    {
        trigger: '.o_notification_bar.bg-success',
        run: function () {
            helper.assertErrorMessage('The transfer has been validated');
        },
    },
]});

registry.category("web_tour.tours").add('test_delivery_duplicate_serial_number', { steps: () => [
    // Create a delivery. Try to scan twice the same serial in different locations.
    { trigger: '.o_stock_barcode_main_menu', run: 'scan WHOUT' },
    { trigger: '.o_scan_message.o_scan_src', run: 'scan LOC-01-01-00' },

    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan productserial1',
    },

    {
        trigger: '.o_barcode_line:contains("productserial1")',
        run: 'scan sn1',
    },
    // Changes the location and scans again the same serial number.
    {
        trigger: '.o_barcode_line .o_line_lot_name:contains("sn1")',
        run: 'scan LOC-01-02-00',
    },

    {
        trigger: '.o_scan_message.o_scan_validate',
        run: 'scan productserial1',
    },

    {
        trigger: '.o_barcode_line:contains("productserial1")',
        run: 'scan sn1',
    },

    {
        trigger: '.o_notification_bar.bg-danger',
        run: function () {
            helper.assertErrorMessage('The scanned serial number sn1 is already used.');
        },
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn2',
    },
    {
        trigger: '.o_barcode_line.o_selected:nth-child(2)',
        run: "click",
    },
    ...stepUtils.validateBarcodeOperation(),

    {
        trigger: '.o_stock_barcode_main_menu',
        run: function () {
            helper.assertErrorMessage('The transfer has been validated');
        },
    },
]});

registry.category("web_tour.tours").add('test_bypass_source_scan', { steps: () => [
    /* Scan directly a serial number, a package or a lot in delivery order.
    * It should implicitely trigger the same action than a source location
    * scan with the state location.
    */
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertLinesCount(3);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan serial1',
    },

    {
        trigger: '.o_barcode_line[data-barcode="productserial1"] .o_edit',
        run: "click",
    },
    {
        trigger: '.o_field_widget[name="qty_done"]',
    },
    {
        trigger: '.o_field_many2one[name=lot_id] input',
        tooltipPosition: "bottom",
        run: "clear",
    },

    {
        trigger: '.o_field_widget[name=qty_done] input',
        run: "edit 0",
    },

    {
        trigger: '.o_save',
        run: "click",
    },

    {
        trigger: '.o_barcode_line',
        run: 'scan lot1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    // Tries to scan a pack in a location the delivery shouldn't have access.
    { trigger: '.o_scan_message.o_scan_product', run: 'scan SUSPACK' },
    {
        trigger: '.o_notification_bar.bg-danger',
        run: function () {
            helper.assertErrorMessage("You are expected to scan one or more products or a package available at the picking location");
        },
    },
    {
        trigger: 'button.o_notification_close',
        run: "click",
    },
    // Scans a package in the right location now.
    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan THEPACK',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan productserial1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan serial1',
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_picking_type_mandatory_scan_settings_pick_int_1', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertLinesCount(2);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(false); // Can't validate until product with barcode was scanned.
            const [ lineProductNoBarcode, lineProduct1 ] = helper.getLines();
            helper.assert(
                lineProduct1.querySelector('.btn.o_edit').disabled, true,
                "Edit button should be disabled until the product was scanned");
            // No button to automatically add the quantity if the product scan is mandatory.
            helper.assertButtonIsVisible(lineProduct1, "add_quantity", false);
            helper.assert(
                lineProductNoBarcode.querySelector('.btn.o_edit').disabled, false,
                "Edit button is always enabled if the product has no barcode (it can't be scanned')");
            // Add quantity button is always displayed if the product has no barcode.
            helper.assertButtonIsVisible(lineProductNoBarcode, "add_remaining_quantity");
            // Checks that locations are still shown despite scanning set to 'no'.
            helper.assertLineLocations(lineProductNoBarcode, "WH/Stock/Section 1", "WH/Stock");
            helper.assertLineLocations(lineProduct1, "WH/Stock/Section 1", "WH/Stock");

        }
    },
    // Scans the source location, it should display an error.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-01-00',
    },
    {
        trigger: '.o_notification_bar.bg-danger',
        run: function() {
            helper.assertErrorMessage("You must scan a product");
        },
    },

    // Scans product1, its buttons should be displayed/enabled.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1',
    },
    {
        trigger: '.o_barcode_line.o_selected',
        run: function() {
            const lineProduct1 = helper.getLine({ barcode: "product1" });
            helper.assert(
                lineProduct1.querySelector('.btn.o_edit').disabled, false,
                "product1 was scanned, the edit button should now be enabled");
            // product1 was scanned, the add quantity button should be visible.
            helper.assertButtonIsVisible(lineProduct1, "add_quantity");
            helper.assertValidateIsHighlighted(false);
            // Since the only product with a barcode was scanned, the validate button is enabled.
            helper.assertValidateEnabled(true);
        }
    },
    // Uses buttons to complete the lines.
    {
        trigger: '.o_barcode_line.o_selected .btn.o_add_remaining_quantity',
        run: "click",
    },
    {
        trigger: '.o_barcode_line .btn.o_add_remaining_quantity',
        run: "click",
    },
    // Lines are completed, the message should ask to validate the operation and that's what we do.
    {
        trigger: 'div[name="barcode_messages"] .fa-check-square',
    },
    {
        trigger: '.btn.o_validate_page.btn-primary',
        run: "click",
    },
    { trigger: '.o_notification_bar.bg-success'},
]});

registry.category("web_tour.tours").add('test_picking_type_mandatory_scan_settings_pick_int_2', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertLinesCount(2);
            helper.assertScanMessage('scan_src');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(false); // Can't validate until product with barcode was scanned.
            const [ lineProductNoBarcode, lineProduct1 ] = helper.getLines();
            helper.assert(
                lineProduct1.querySelector('.btn.o_edit').disabled, true,
                "Edit button should be disabled until the product was scanned");
            // No button to automatically add the quantity if the product scan is mandatory.
            helper.assertButtonIsVisible(lineProduct1, "add_quantity", false);
            helper.assert(
                lineProductNoBarcode.querySelector('.btn.o_edit').disabled, true,
                "All lines' buttons are disabled until a source location was scanned");
            helper.assert(
                lineProductNoBarcode.querySelector('.btn.o_add_remaining_quantity').disabled, true,
                "All lines' buttons are disabled until a source location was scanned");
        }
    },
    // Scans a product, it should display an error.
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    {
        trigger: '.o_notification:has(.o_notification_bar.bg-danger)',
        run: function() {
            helper.assertErrorMessage(
                "You are supposed to scan WH/Stock or another source location");
        },
    },
    {
        trigger: '.btn-close.o_notification_close',
        run: "click",
    },

    // Scans the source location, the buttons for the product without barcode should be enabled.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-00-00',
    },
    {
        trigger: '.o_scan_message.o_scan_product',
        run: function () {
            const [ lineProductNoBarcode, lineProduct1 ] = helper.getLines();
            helper.assert(
                lineProduct1.querySelector('.btn.o_edit').disabled, true,
                "Edit button should be disabled until the product was scanned");
            helper.assert(
                lineProduct1.querySelector('.btn.o_add_remaining_quantity').disabled, true,
                "Button to automatically add the quantity is disabled if the product scan is mandatory");
            helper.assert(
                lineProductNoBarcode.querySelector('.btn.o_edit').disabled, false,
                "Since the source of this line was scanned and it has no barcode, its buttons should be enabled");
            helper.assert(
                lineProductNoBarcode.querySelector('.btn.o_add_remaining_quantity').disabled, false,
                "Since the source of this line was scanned and it has no barcode, its buttons should be enabled");
        }
    },
    // Scans another location, it replaces the previous scanned source as no product was scanned yet.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-01-00',
    },

    // Scans product1.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1',
    },
    {
        trigger: '.o_barcode_line.o_selected',
        run: function() {
            const lineProduct1 = helper.getLine({ barcode: "product1" });
            helper.assert(
                lineProduct1.querySelector('.btn.o_edit').disabled, false,
                "product1 was scanned, the edit button should now be enabled");
            // product1 was scanned, the add quantity button should be visible.
            helper.assertButtonIsVisible(lineProduct1, "add_quantity");
            helper.assertValidateIsHighlighted(false);
            // Since the only product with a barcode was scanned, the validate button is enabled.
            helper.assertValidateEnabled(true);
        }
    },
    // Scans another product: it should raise an error as the destination should be scanned between each product.
    { trigger: '.o_barcode_client_action', run: 'scan product2' },
    {
        trigger: '.o_notification_bar.bg-danger',
        run: function() {
            helper.assertErrorMessage(
                "Please scan destination location for product1 before scanning other product");
        },
    },
    {
        trigger: '.btn-close.o_notification_close',
        run: "click",
    },

    // Uses button to complete the line, then scan the destination.
    {
        trigger: '.o_barcode_line.o_selected .btn.o_add_remaining_quantity',
        run: "click",
    },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: 'scan LOC-01-00-00',
    },
    // Scans again product1: should raise an error as it expects the source (should be scanned after each product).
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    {
        trigger: '.o_notification_bar.bg-danger',
        run: function() {
            helper.assertErrorMessage(
                "You are supposed to scan WH/Stock or another source location");
        },
    },
    {
        trigger: '.btn-close.o_notification_close',
        run: "click",
    },

    // Scans the source and updates the remaining product qty with its button (because no barcode).
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-01-00',
    },
    {
        trigger: '.o_scan_message.o_scan_product',
    },
    {
        trigger: '.o_barcode_line .btn.o_add_remaining_quantity',
        run: "click",
    },
    // Tries to validate without scanning the destination: display a warning.
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: 'scan OBTVALI',
    },
    {
        trigger: '.o_notification:has(.o_notification_bar.bg-danger) .o_notification_close.btn-close',
        run: "click",
    },

    // Scans the destination location than validate the operation.
    {
        trigger: 'div[name="barcode_messages"] .fa-sign-in', // "Scan dest. loc." message's icon.
        run: 'scan LOC-01-00-00',
    },
    {
        trigger: 'div[name="barcode_messages"] .fa-check-square',
    },
    {
        trigger: '.btn.o_validate_page.btn-primary',
        run: "click",
    },
    { trigger: '.o_notification_bar.bg-success'},
]});

registry.category("web_tour.tours").add('test_receipt_scan_package_and_location_after_group_of_product', { steps: () => [
    {
        trigger: ".o_barcode_client_action",
        run: function () {
            helper.assertLinesCount(3);
            helper.assertLineProduct(0, "Barcodeless Product");
            helper.assertLineProduct(1, "product1");
            helper.assertLineProduct(2, "productlot1");
        }
    },
    // Scans 2x product1...
    { trigger: ".o_barcode_line", run: "scan product1" },
    { trigger: ".o_barcode_line.o_selected", run: "scan product1" },
    // ... process all the products with no barcode and 3 productlot1 (2 differents lots).
    {
        trigger: ".o_barcode_line.o_selected .qty-done:contains(2)",
    },
    {
        trigger: ".o_barcode_line:not([data-barcode]) .o_line_button.o_add_remaining_quantity",
        run: "click",
    },
    // ... and scans 3 productlot1 from 2 differents lots.
    { trigger: ".o_barcode_line.o_selected.o_line_completed", run: "scan productlot1" },
    { trigger: ".o_barcode_line[data-barcode='productlot1'].o_selected", run: "scan lot-01" },
    { trigger: ".o_barcode_line", run: "scan lot-01" },
    { trigger: ".o_barcode_line", run: "scan lot-02" },

    // Scans Section 1, the destination should be applied to all previous scanned lines and
    // the edited line. For the uncompleted lines, they should be split in two:
    // - one line with the processed quantity going to the scanned location;
    // - one line with the remaining quantity going to the picking's location.
    { trigger: ".o_barcode_line.o_selected .o_toggle_sublines", run: "scan LOC-01-01-00" },
    {
        trigger: ".o_barcode_line:nth-child(5)",
        run: function () {
            helper.assertLinesCount(5);

            helper.assertLineProduct(0, "Barcodeless Product");
            helper.assertLineQty(0, "4/4");
            helper.assertLineDestinationLocation(0, ".../Section 1");

            helper.assertLineProduct(1, "product1");
            helper.assertLineQty(1, "2/2");
            helper.assertLineDestinationLocation(1, ".../Section 1");

            helper.assertLineProduct(2, "product1");
            helper.assertLineQty(2, "0/2");
            helper.assertLineDestinationLocation(2, "WH/Stock");

            helper.assertLineProduct(3, "productlot1");
            helper.assertLineQty(3, "3/3");
            helper.assertLineDestinationLocation(3, ".../Section 1");

            helper.assertLineProduct(4, "productlot1");
            helper.assertLineQty(4, "0/3");
            helper.assertLineDestinationLocation(4, "WH/Stock");
        }
    },

    // Scan only one lot then another destination. Only this lot should be moved to this location.
    { trigger: ".o_barcode_client_action", run: "scan productlot1" },
    { trigger: ".o_scan_message.o_scan_lot", run: "scan lot-02" },
    {
        trigger: ".o_barcode_line.o_selected .o_line_lot_name:contains('lot-02')",
        run: "scan LOC-01-02-00",
    },

    {
        trigger: ".o_scan_message.o_scan_product",
        run: function () {
            helper.assertLinesCount(6);

            helper.assertLineProduct(0, "Barcodeless Product");
            helper.assertLineQty(0, "4/4");
            helper.assertLineDestinationLocation(0, ".../Section 1");

            helper.assertLineProduct(1, "product1");
            helper.assertLineQty(1, "2/2");
            helper.assertLineDestinationLocation(1, ".../Section 1");

            helper.assertLineProduct(2, "product1");
            helper.assertLineQty(2, "0/2");
            helper.assertLineDestinationLocation(2, "WH/Stock");

            helper.assertLineProduct(3, "productlot1");
            helper.assertLineQty(3, "3/3");
            helper.assertLineDestinationLocation(3, ".../Section 1");

            helper.assertLineProduct(4, "productlot1");
            helper.assertLineQty(4, "1/1");
            helper.assertLineDestinationLocation(4, ".../Section 2");

            helper.assertLineProduct(5, "productlot1");
            helper.assertLineQty(5, "0/2");
            helper.assertLineDestinationLocation(5, "WH/Stock");
        }
    },

    // Process the remaining quantity then scans an existing package: only those lines should be packed.
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    { trigger: ".o_barcode_line.o_selected", run: "scan product1" },
    { trigger: ".o_barcode_line.o_selected.o_line_completed", run: "scan productlot1" },
    { trigger: ".o_barcode_line.o_selected:not(.o_line_completed)", run: "scan lot-03" },
    { trigger: ".o_barcode_line.o_selected:not(.o_line_completed)", run: "scan lot-03" },
    { trigger: ".o_barcode_line.o_selected.o_line_completed", run: "scan pack-128" },
    // Scans another destination: only the packaged lines should go to this location.
    { trigger: ".o_barcode_line [name='package']", run: "scan shelf3" },
    {
        trigger: ".o_scan_message.o_scan_validate",
        run: function () {
            helper.assertLinesCount(6);

            helper.assertLineProduct(0, "Barcodeless Product");
            helper.assertLineQty(0, "4/4");
            helper.assertLineDestinationLocation(0, ".../Section 1");

            helper.assertLineProduct(1, "product1");
            helper.assertLineQty(1, "2/2");
            helper.assertLineDestinationLocation(1, ".../Section 1");

            let line = helper.getLine({ index: 2 });
            helper.assertLineProduct(line, "product1");
            helper.assertLineQty(line, "2/2");
            helper.assertLineDestinationLocation(line, ".../Section 3");
            helper.assert(line.querySelector('[name="package"]').innerText, "pack-128");

            helper.assertLineProduct(3, "productlot1");
            helper.assertLineQty(3, "3/3");
            helper.assertLineTrackingNumber(3, false);
            helper.assertLineDestinationLocation(3, ".../Section 1");

            helper.assertLineProduct(4, "productlot1");
            helper.assertLineQty(4, "1/1");
            helper.assertLineTrackingNumber(4, "lot-02");
            helper.assertLineDestinationLocation(4, ".../Section 2");

            line = helper.getLine({ index: 5 });
            helper.assertLineProduct(5, "productlot1");
            helper.assertLineQty(5, "2/2");
            helper.assertLineTrackingNumber(5, "lot-03");
            helper.assertLineDestinationLocation(5, ".../Section 3");
            helper.assert(line.querySelector('[name="package"]').innerText, "pack-128");
        }
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_receipt_assign_sibling_reservation_no_empty_line', { steps: () => [
    {
        trigger: ".o_barcode_client_action",
        run: function () {
            helper.assertLinesCount(1);
            helper.assertLineProduct(0, "productlot1");
        }
    },
    { trigger: ".o_barcode_line", run: "scan productlot1" },
    { trigger: ".o_barcode_line[data-barcode='productlot1']", run: "scan lot-01" },
    { trigger: ".o_barcode_line[data-barcode='productlot1']", run: "scan lot-02" },

    // Select first line to ensure that the dest location change is done on the line with reserved quantity
    { trigger: "button.o_line_button.o_toggle_sublines", run: "click" },
    { trigger: ".o_sublines > .o_barcode_line[data-barcode='productlot1']:first-child", run: "click" },

    // Change dest location, this should re-assign the reserved quantity
    { trigger: ".o_barcode_line.o_selected", run: "scan LOC-01-01-00" },
    {
        trigger: ".o_barcode_location_group>.o_barcode_line .o_line_destination_location:contains('Section 1')",
        run: function () {
            helper.assertLinesCount(1);
            helper.assertLineProduct(0, "productlot1");
            helper.assertLineQty(0, "2/2");
            helper.assertLineDestinationLocation(0, ".../Section 1");
        }
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_picking_type_mandatory_scan_product_packaging', { steps: () => [
    {
        trigger: '.o_barcode_line',
        run: () => {
            helper.assertScanMessage("scan_product");
            helper.assert(Boolean(document.querySelector('button.o_edit[disabled]')), true,
                "Edit button should be visible but disabled");
        }
    },
    { trigger: '.o_barcode_line', run: "scan product1x10" },
    { trigger: '.o_barcode_line.o_selected.o_line_completed' },

]});

registry.category("web_tour.tours").add('test_picking_type_mandatory_scan_complete_flux_receipt', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(5);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(false); // Can't validate until product with barcode was scanned.
        }
    },
    // Scans product1 two times to complete the lines.
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: function() {
            helper.assertScanMessage('scan_product_or_dest');
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true); // Can't validate until product with barcode was scanned.
        }
    },
    // Process product2 and product with no barcode with the button.
    {
        trigger: '.o_barcode_line[data-barcode="product2"] .btn.o_add_remaining_quantity',
        run: "click",
    },
    {
        trigger: '.o_barcode_line[data-barcode="product2"].o_line_completed',
    },
    {
        trigger: '.o_barcode_line:not([data-barcode]) .btn.o_add_remaining_quantity',
        run: "click",
    },
    // Before to scan remaining product, scans a first time the destination.
    {
        trigger: '.o_barcode_line:not([data-barcode]).o_line_completed',
        run: 'scan WHINPUT'
    },
    // The message should ask to scan a product, so scans product tracked by lots.
    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan productlot1'
    },
    // Scans lot-001 x2, lot-002 x2 and lot-003 x2.
    {
        trigger: '.o_barcode_line[data-barcode="productlot1"].o_selected',
        run: 'scan lot-001'
    },
    { trigger: '.o_barcode_line', run: 'scan lot-001' },
    { trigger: '.o_barcode_line', run: 'scan lot-002' },
    { trigger: '.o_barcode_line', run: 'scan lot-002' },
    { trigger: '.o_barcode_line', run: 'scan lot-003' },
    { trigger: '.o_barcode_line', run: 'scan lot-003' },
    {
        trigger: '.o_barcode_line[data-barcode="productlot1"].o_selected.o_line_completed',
        run: function() {
            helper.assertScanMessage('scan_product_or_dest');
        }
    },
    // Scans the product tracked by serial numbers and scans three serials.
    {
        trigger: '.o_scan_message.o_scan_product_or_dest',
        run: 'scan productserial1'
    },
    {
        trigger: '.o_barcode_line[data-barcode="productserial1"].o_selected',
        run: 'scan sn-001'
    },
    { trigger: '.o_barcode_line', run: 'scan sn-002' },
    { trigger: '.o_barcode_line', run: 'scan sn-003' },
    // It should ask to scan the destination, so scans it.
    {
        trigger: 'div[name="barcode_messages"] .o_scan_product_or_dest',
        run: 'scan WHINPUT',
    },
    // Now the destination was scanned, it should say the operation can be validate.
    {
        trigger: 'div[name="barcode_messages"] .o_scan_validate',
    },
    {
        trigger: '.o_validate_page.btn-primary',
        run: "click",
    },
    {
        trigger: '.o_notification_bar.bg-success',
    },
]});

registry.category("web_tour.tours").add('test_picking_type_mandatory_scan_complete_flux_internal', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(5);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(false); // Can't validate until product with barcode was scanned.
        }
    },
    // Scans one product1 to move in Section 1, but scans another product between.
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    { trigger: '.o_barcode_line.o_selected', run: 'scan product2' }, // Should raise an error.
    {
        trigger: '.o_notification:has(.o_notification_bar.bg-danger)',
        run: function() {
            helper.assertErrorMessage(
                "Please scan destination location for product1 before scanning other product");
        },
    },
    {
        trigger: '.btn-close.o_notification_close',
        run: "click",
    },

    { // Scans the destination (Section 1).
        trigger: '.o_barcode_line.o_selected',
        run: 'scan LOC-01-01-00'
    },
    // product1 line is split, 1 qty moves to Section 1, the rest is left as default
    {
        trigger: '.o_barcode_line.o_line_completed .o_line_destination_location .fw-bold:contains("Section 1")',
    },
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(6);
            helper.assertScanMessage('scan_product');
        },
    },

    // Scans product1 again and move it to Section 3.
    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan product1'
    },
    {
        trigger: '.o_barcode_line.o_selected',
        run: 'scan shelf3'
    },

    // Scans product2 and moves it into Section 2.
    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan product2'
    },
    {
        trigger: '.o_barcode_line.o_selected',
        run: 'scan LOC-01-02-00'
    },

    // Process quantities for the product with no barcode and move it to Section 1.
    {
        trigger: '.o_scan_message.o_scan_product',
    },
    {
        trigger: '.o_barcode_line:not([data-barcode]) .btn.o_add_remaining_quantity',
        run: "click",
    },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: 'scan LOC-01-01-00'
    },

    // The message should ask to scan a product, so scans product tracked by lots.
    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan productlot1'
    },
    // Scans lot-001 x2, lot-002 x2 and moves them in Section 3.
    {
        trigger: '.o_barcode_line[data-barcode="productlot1"].o_selected',
        run: 'scan lot-001'
    },
    {
        trigger: '.o_barcode_line.o_selected .btn.o_toggle_sublines .fa-angle-down',
        run: "click",
    },
    {
        trigger: '.o_sublines .o_barcode_line.o_selected',
        run: 'scan lot-001'
    },
    {
        trigger: '.o_sublines .o_barcode_line.o_selected.o_line_completed',
        run: 'scan lot-002'
    },
    {
        trigger: '.o_sublines .o_barcode_line.o_selected:not(.o_line_completed)',
        run: 'scan lot-002'
    },
    {
        trigger: '.o_sublines .o_barcode_line.o_selected.o_line_completed',
        run: 'scan shelf3'
    },

    // Scans lot-003 x2 and moves them in Section 4.
    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan lot-003'
    },
    {
        trigger: '.o_barcode_line[data-barcode="productlot1"].o_selected',
        run: 'scan lot-003'
    },
    {
        trigger: '.o_barcode_line[data-barcode="productlot1"].o_selected',
        run: 'scan shelf4'
    },

    // Scans the product tracked by serial numbers and scans three serials.
    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan productserial1'
    },
    {
        trigger: '.o_barcode_line[data-barcode="productserial1"].o_selected',
        run: 'scan sn-001'
    },
    {
        trigger: '.o_barcode_line[data-barcode="productserial1"].o_selected',
        run: 'scan sn-002'
    },
    {
        trigger: '.o_barcode_line[data-barcode="productserial1"].o_selected',
        run: 'scan sn-003'
    },
    { // Moves it to Section 4.
        trigger: '.o_barcode_line[data-barcode="productserial1"].o_selected.o_line_completed',
        run: 'scan shelf4'
    },
    // It should say the operation can be validate.
    {
        trigger: 'div[name="barcode_messages"] .fa-check-square', // "Press validate" message icon.
    },
    {
        trigger: '.o_validate_page.btn-primary',
        run: "click",
    },
    {
        trigger: '.o_notification_bar.bg-success',
    },
]});

registry.category("web_tour.tours").add('test_picking_type_mandatory_scan_complete_flux_pick', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(7);
            helper.assertScanMessage('scan_src');
            helper.assertValidateVisible(true);
            helper.assertValidateEnabled(false);
            const lineButtons = document.querySelectorAll('.btn.o_edit,.btn.o_add_remaining_quantity');
            helper.assert(lineButtons.length, 10, "Should have 1 edit & 1 add qty. buttons on 5 lines");
            for (const button of lineButtons) {
                helper.assert(button.disabled, true,
                    "All lines' buttons are disabled until a source location was scanned");
            }
        }
    },
    // Scans product1 -> raise an error because it expects the source location.
    {
        trigger: '.o_scan_message.o_scan_src',
        run: 'scan product1'
    },
    {
        trigger: '.o_notification',
        run: function() {
            helper.assertErrorMessage(
                "You are supposed to scan WH/Stock or another source location");
        },
    },
    {
        trigger: '.btn-close.o_notification_close',
        run: "click",
    },

    // Scan another location (Section 2 for the instance).
    {
        trigger: '.o_scan_message.o_scan_src',
        run: 'scan LOC-01-02-00'
    },
    {
        trigger: '.o_barcode_location_line[data-location="WH/Stock/Section 2"].text-bg-800',
        run: function() {
            helper.assertLinesCount(7);
            helper.assertScanMessage('scan_product');
            const lineProduct2 = document.querySelector('.o_barcode_line');
            helper.assert(
                lineProduct2.querySelector('.btn.o_edit').disabled, false,
                "Since the source location was scanned, its buttons should be enabled");
            helper.assert(
                lineProduct2.querySelector('.btn.o_add_remaining_quantity').disabled, false,
                "Since the source location was scanned, its buttons should be enabled");
        }
    },
    // Scans product2 then scans another source location (Section 3) => Should raise a warning.
    { trigger: '.o_barcode_client_action', run: 'scan product2' },
    { trigger: '.o_barcode_line.o_line_completed', run: 'scan shelf3' },
    {
        trigger: '.o_notification',
        run: function() {
            helper.assertErrorMessage("You must scan a package or put in pack");
        },
    },
    {
        trigger: '.btn-close.o_notification_close',
        run: "click",
    },

    // Scans a pack then scans Section 1.
    { trigger: '.o_barcode_line.o_line_completed', run: 'scan cluster-pack-01' },
    { trigger: '.o_barcode_line.o_selected .result-package', run: 'scan LOC-01-01-00' },
    {
        trigger: '.o_barcode_location_line[data-location="WH/Stock/Section 1"].text-bg-800',
        run: function() {
            helper.assertLinesCount(7);
            helper.assertScanMessage('scan_product');
        }
    },
    // Scans product1 from Section 1, pack it.
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    { trigger: '.o_barcode_line[data-barcode="product1"].o_selected', run: 'scan cluster-pack-01' },
    // Do the same from Section 3
    { trigger: '.o_barcode_line.o_line_completed .result-package', run: 'scan shelf3' },
    { trigger: '.o_barcode_location_line[data-location="WH/Stock/Section 3"].text-bg-800', run: 'scan product1' },
    {
        trigger: '.o_barcode_location_line[data-location="WH/Stock/Section 3"] + .o_barcode_line.o_selected.o_line_completed',
        run: 'scan productlot1'
    },
    {
        trigger: '.o_notification',
        run: function() {
            helper.assertErrorMessage("You must scan a package or put in pack");
        },
    },
    {
        trigger: '.btn-close.o_notification_close',
        run: "click",
    },
    { trigger: '.o_barcode_client_action', run: 'scan cluster-pack-01' },
    // scans lot-001 and lot-002
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed .result-package',
        run: 'scan productlot1'
    },
    // Checks we can't edit a line for a tracked product until the tracking number was scan.
    {
        trigger: '.o_barcode_line.o_selected .btn.o_toggle_sublines .fa-angle-down',
        run: "click",
    },
    {
        trigger: '.o_barcode_line.o_selected .o_sublines',
        run: function() {
            const [ lot001Line, lot002Line ] = helper.getSublines();
            helper.assert(lot001Line.querySelector('.btn.o_add_quantity').disabled, true,
                "Lot number not scanned yet, so line's buttons are disabled.");
            helper.assert(lot001Line.querySelector('.btn.o_add_remaining_quantity').disabled, true,
                "Lot number not scanned yet, so line's buttons are disabled.");
            helper.assert(lot002Line.querySelector('.btn.o_add_remaining_quantity').disabled, true,
                "Lot number not scanned yet, so line's buttons are disabled.");
        }
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot-001',
    },
    {
        trigger: '.o_barcode_line.o_selected .qty-done:contains(1)',
        run: function() {
            const [ lot001Line, lot002Line ] = helper.getSublines();
            helper.assert(lot001Line.querySelector('.btn.o_remove_unit').disabled, false,
                "lot-001 was scanned, its line's buttons should be enable");
            helper.assert(lot001Line.querySelector('.btn.o_add_remaining_quantity').disabled, false,
                "lot-001 was scanned, its line's buttons should be enable");
            helper.assert(lot002Line.querySelector('.btn.o_add_remaining_quantity').disabled, true,
                "Lot number not scanned yet, so line's buttons are disabled.");
        }
    },
    {
        trigger: '.o_barcode_line.o_selected:not(.o_line_completed)',
        run: 'scan lot-001',
    },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: function() {
            const lot001Line = helper.getSubline({ completed: true });
            const lot002Line = helper.getSubline({ completed: false });
            helper.assertButtonIsVisible(lot001Line, "remove_unit");
            helper.assertButtonIsVisible(lot001Line, "add_quantity", false);
            helper.assertButtonIsVisible(lot001Line, "add_remaining_quantity");
            helper.assert(lot002Line.querySelector('.btn.o_add_remaining_quantity').disabled, true);
        }
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot-002',
    },
    {
        trigger: '.o_barcode_line.o_selected .qty-done:contains(1)',
        run: function() {
            const lot002Line = helper.getSubline({ selected: true, completed: false});
            helper.assert(lot002Line.querySelector('.btn.o_remove_unit').disabled, false,
                "lot-002 was scanned, the button to remove quantity should be enabled.");
            helper.assert(lot002Line.querySelector('.btn.o_add_remaining_quantity').disabled, false,
                "lot-002 was scanned, the button to add quantity should be enabled.");
        }
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot-002',
    },

    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: function() {
            const lot002Line = helper.getSubline({ selected: true, completed: true});
            helper.assertButtonIsVisible(lot002Line, "remove_unit");
            helper.assertButtonIsVisible(lot002Line, "add_quantity", false);
            helper.assertButtonIsVisible(lot002Line, "add_remaining_quantity", false);
        }
    },
    { trigger: '.o_barcode_client_action', run: 'scan cluster-pack-02' },

    // Scans Section 1 (source) and processes the remaining products.
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed .result-package',
        run: 'scan LOC-01-01-00',
    },
    {
        trigger: '.o_barcode_location_line[data-location="WH/Stock/Section 1"].text-bg-800',
    },
    {
        trigger: '.o_barcode_line:not([data-barcode]) .btn.o_add_remaining_quantity',
        run: "click",
    },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed:not([data-barcode])',
        run: 'scan cluster-pack-01'
    },

    // Scans Section 4 (source).
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed .result-package',
        run: 'scan shelf4'
    },
    // Scans the remaining lot and the serial numbers.
    {
        trigger: '.o_scan_message.o_scan_product',
    },
    {
        trigger: '.o_barcode_location_line[data-location="WH/Stock/Section 4"].text-bg-800',
        run: 'scan lot-003',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn-001',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn-003',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn-002',
    },
    {
        trigger: '.o_scan_message.o_scan_package',
    },
    {
        trigger: '.o_barcode_line[data-barcode="productserial1"].o_selected.o_line_completed',
        run: 'scan cluster-pack-02'
    },
    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan lot-003',
    },
    {
        trigger: '.o_barcode_line[data-barcode="productlot1"].o_selected.o_line_completed',
        run: 'scan cluster-pack-02'
    },
    // It should say the operation can be validate.
    {
        trigger: 'div[name="barcode_messages"] .fa-check-square', // "Press validate" message icon.
    },
    {
        trigger: '.o_validate_page.btn-primary',
        run: "click",
    },
    {
        trigger: '.o_notification_bar.bg-success',
    },
]});

registry.category("web_tour.tours").add('test_picking_type_mandatory_scan_complete_flux_pack', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(5);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateEnabled(true);
            helper.assertValidateIsHighlighted(false);
        }
    },
    // Scans first cluster pack.
    { trigger: '.o_barcode_client_action', run: 'scan cluster-pack-01'},
    // Scans second cluster pack.
    { trigger: '.o_barcode_client_action', run: 'scan cluster-pack-02'},
    // Tries to validate: it should ask to put in pack.
    {
        trigger: '.o_validate_page.btn-primary',
        run: "click",
    },
    {
        trigger: '.o_notification',
        run: function() {
            helper.assertErrorMessage("All products need to be packed");
        },
    },
    {
        trigger: '.btn-close.o_notification_close',
        run: "click",
    },
    // Puts in pack.
    { trigger: '.o_barcode_client_action', run: 'scan OBTPACK'},
    // Validates the operation.
    {
        trigger: '.o_scan_message.o_scan_validate',
    },
    {
        trigger: '.o_validate_page.btn-primary',
        run: "click",
    },
    { trigger: '.o_notification_bar.bg-success'},
]});

registry.category("web_tour.tours").add('test_picking_type_mandatory_scan_complete_flux_delivery', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(1);
            helper.assertScanMessage('scan_product_or_package');
        }
    },
    // Scans the pack, then validate.
    {
        trigger: '.o_barcode_line:contains("PACK0000001")',
        run: 'scan PACK0000001'
    },
    // It should say the operation can be validate.
    {
        trigger: '.o_scan_message.o_scan_validate', // "Press validate" message icon.
    },
    {
        trigger: '.o_barcode_line.o_line_completed',
        run: 'scan OBTVALI',
    },
    { trigger: '.o_notification_bar.bg-success'},
]});

registry.category("web_tour.tours").add('test_pack_multiple_scan', { steps: () => [
    // Create a receipt, scan product1 and product2, pack them and validate the receipt.
    { trigger: '.o_stock_barcode_main_menu', run: 'scan WHIN' },
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    { trigger: '.o_barcode_client_action', run: 'scan product2' },
    { trigger: '.o_barcode_line + .o_barcode_line', run: 'scan OBTPACK' },
    ...stepUtils.validateBarcodeOperation(),
    {
        trigger: '.o_stock_barcode_main_menu',
        run: function () {
            helper.assertErrorMessage('The transfer has been validated');
        },
    },
    { trigger: ".o_notification_close", run: "click" },

    // Create a delivery, scan two times the same package and check the error message.
    { trigger: '.o_stock_barcode_main_menu', run: 'scan WHOUT' },
    { trigger: '.o_barcode_client_action', run: 'scan PACK0001000' },
    {
        trigger: '.o_barcode_line',
        run: function () {
            const line1 = helper.getLine({ barcode: "product1" });
            helper.assertLineIsHighlighted(line1, true);
            const line2 = helper.getLine({ barcode: "product2" });
            helper.assertLineIsHighlighted(line2, true);
        },
    },
    { trigger: '.o_barcode_line:nth-child(2)', run: 'scan PACK0001000' },
    {
        trigger: '.o_notification_bar.bg-danger',
        run: function () {
            helper.assertErrorMessage('This package is already scanned.');
            helper.assertLineIsHighlighted(0, false);
            helper.assertLineIsHighlighted(0, false);
        },
    },
    ...stepUtils.validateBarcodeOperation(),
    {
        trigger: '.o_stock_barcode_main_menu',
        run: function () {
            helper.assertErrorMessage('The transfer has been validated');
        },
    },
]});

registry.category("web_tour.tours").add('test_pack_common_content_scan', { steps: () => [
    /* Scan 2 packages PACK1 and PACK2 that contains both product1 and
     * product 2. It also scan a single product1 before scanning both packages.
     * The purpose is to check that lines with a same product are not merged
     * together. For product 1, we should have 3 lines. One with PACK 1, one
     * with PACK2 and the last without package.
     */
    {
        trigger: '.o_stock_barcode_main_menu',
        run: 'scan WHOUT',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan PACK1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan PACK2',
    },

    {
        trigger: '.o_barcode_client_action:contains("PACK2")',
        run: function () {
            helper.assertLinesCount(5);
        },
    },
    ...stepUtils.validateBarcodeOperation(),

    {
        trigger: '.o_stock_barcode_main_menu',
        run: function () {
            helper.assertErrorMessage('The transfer has been validated');
        },
    },
]});

registry.category("web_tour.tours").add('test_pack_multiple_location', { steps: () => [
    {
        trigger: '.o_stock_barcode_main_menu',
        run: 'scan WHINT',
    },

    {
        trigger: '.o_barcode_client_action .o_scan_message.o_scan_src',
        run: 'scan LOC-01-01-00'
    },

    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan PACK0000666',
    },

    {
        trigger: '.o_package_content',
        run: () => helper.assertLineQty(0, "1")
    },

    { // Scan a second time the same package => Should raise a warning.
        trigger: '.o_barcode_client_action',
        run: 'scan PACK0000666',
    },
    { // A notification is shown and the package's qty. should be unchanged.
        trigger: '.o_notification_bar.bg-danger',
        run: () => helper.assertLineQty(0, "1")
    },

    {
        trigger: '.o_package_content',
        run: "click",
    },
    {
        trigger: '.o_kanban_view:contains("product1")',
        run: function () {
            helper.assertKanbanRecordsCount(2);
        },
    },
    {
        trigger: '.o_close',
        run: "click",
    },

    {
        trigger: '.o_scan_message.o_scan_dest',
        run: 'scan LOC-01-02-00',
    },

    ...stepUtils.validateBarcodeOperation(".o_scan_message.o_scan_validate"),

    {
        trigger: '.o_stock_barcode_main_menu',
        run: function () {
            helper.assertErrorMessage('The transfer has been validated');
        },
    },
]});

registry.category("web_tour.tours").add('test_pack_multiple_location_02', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-01-00'
    },

    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan PACK0002020',
    },
    {
        trigger: '.o_barcode_line.o_selected',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-02-00',
    },

    {
        trigger: '.o_barcode_line .o_line_destination_location:contains("WH/Stock/Section 2")',
        run: 'scan OBTVALI',
    },

    {
        trigger: '.o_notification_bar.bg-success',
    },
]});

registry.category("web_tour.tours").add('test_pack_multiple_location_03', { steps: () => [
    {trigger: '.o_barcode_client_action', run: 'scan shelf3'},
    {
        trigger: '.o_barcode_line',
        run: function() {
            helper.assertLinesCount(1);
            helper.assert(document.querySelector('.o_barcode_line .package').textContent, "PACK000666");
        }
    },
    {trigger: '.o_barcode_client_action', run: 'scan product1'},
    {
        trigger: '.qty-done:contains(1)',
        run: function() {
            helper.assertLinesCount(1);
            helper.assert(document.querySelectorAll('.o_barcode_lines .o_barcode_line .package').length, 0);
        }
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_pack_source_location', { steps: () => [
    {
        trigger: '.o_stock_barcode_main_menu',
        run: 'scan WHINT',
    },
    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan PACK123666',
    },
    {
        trigger: '.o_barcode_line',
        run: function() {
            const line = helper.getLine({ barcode: 'product1' });
            helper.assertLineSourceLocation(line, "WH/Stock/Section 4");
        },
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_put_in_pack_from_multiple_pages', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertLinesCount(4);
            helper.assertScanMessage('scan_src');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
        },
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-01-00'
    },

    {
        trigger: '.o_scan_message.o_scan_product',
        run: function () {
            helper.assertLinesCount(4);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
        },
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2',
    },

    {
        trigger: '.o_barcode_line:nth-child(2).o_line_completed',
        run: 'scan LOC-01-02-00',
    },

    {
        trigger: '.o_scan_message:contains("Scan a product from Section 2")',
        run: 'scan product1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2',
    },

    {
        trigger: '.o_validate_page.btn-primary',
        run: 'scan OBTPACK',
    },

    ...stepUtils.validateBarcodeOperation('.o_barcode_line:contains("PACK")'),
]});

registry.category("web_tour.tours").add('test_put_in_pack_no_freeze', { steps: () => [
    { trigger: 'button.o_button_operations', run: 'click' },

    { trigger: '.o_kanban_record:contains(Receipts)', run: 'click' },

    { trigger: 'button[name="action_open_picking_client_action"]:last', run: 'click' },

    { trigger: '.o_edit', run: "click" },

    {
        trigger: '.o_field_widget[name=qty_done] input',
        run() {
            //input type number not supported by tour helpers.
            this.anchor.value = "5.66";
        }
    },

    { trigger: '.o_save', run: 'click' },

    { trigger: '.o_put_in_pack', run: 'click' },

    { trigger: 'button.o_exit', run: 'click' },
]});

registry.category("web_tour.tours").add('test_reload_flow', { steps: () => [
    {
        trigger: '.o_stock_barcode_main_menu',
        run: 'scan WHIN'
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.o_edit',
        run: "click",
    },
    {
        trigger: '.o_field_widget[name="product_id"]',
    },
    {
        trigger: '.o_field_widget[name=qty_done] input',
        run: "edit 2",
    },

    {
        trigger: '.o_save',
        run: "click",
    },

    {
        trigger: '.o_add_line',
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
        trigger: '.o_save',
        run: "click",
    },

    {
        trigger: '.o_barcode_line:nth-child(2).o_selected',
        run: function () {
            helper.assertScanMessage('scan_product_or_dest');
        },
    },

    { trigger: '.o_barcode_client_action', run: 'scan LOC-01-01-00' },
    // Select first line and scans Section 1 to move it to this location.
    {
        trigger: '.o_barcode_line:nth-child(2) .o_line_destination_location:contains(".../Section 1")',
    },
    {
        trigger: '.o_barcode_line:first-child',
        run: "click",
    },
    {
        trigger: '.o_barcode_line:first-child.o_selected',
        run: 'scan LOC-01-01-00'
    },
    {
        trigger: '.o_barcode_line:nth-child(1) .o_line_destination_location:contains(".../Section 1")',
        run: "click",
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_highlight_packs', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertLinesCount(1);
            helper.assertScanMessage('scan_product_or_package');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
            helper.assertLineIsHighlighted(0, false);

        },
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan PACK002',
    },

    {
        trigger: '.o_barcode_client_action:contains("PACK002")',
        run: "click",
    },

    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertLinesCount(2);
            helper.assertScanMessage('scan_product_or_package');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
            const packageLine = document.querySelector('.o_barcode_line[data-package="PACK002"]');
            helper.assertLineIsHighlighted(packageLine, true);
        },
    },

]});

registry.category("web_tour.tours").add('test_put_in_pack_from_different_location', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1',
    },

    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: 'scan product2',
    },

    {
        trigger: '.o_validate_page.btn-primary',
        run: 'scan OBTPACK',
    },

    {
        trigger: '.o_barcode_line:contains("PACK")',
        run: function() {
            const lines = helper.getLines();
            helper.assert(lines[0].querySelector('.result-package').innerText, "PACK0000001");
            helper.assert(lines[1].querySelector('.result-package').innerText, "PACK0000001");
        },
    },
    // Scans dest. location.
    {
        trigger: '.o_scan_message.o_scan_product_or_dest',
        run: 'scan LOC-01-02-00',
    },
    ...stepUtils.validateBarcodeOperation('.o_scan_message.o_scan_validate'),
]});

registry.category("web_tour.tours").add('test_put_in_pack_before_dest', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-01-00',
    },

    {
        trigger: '.o_barcode_location_line[data-location="WH/Stock/Section 1"].text-bg-800',
        run: 'scan product1',
    },
    { trigger: '.o_scan_message.o_scan_product_or_dest', run: 'scan LOC-01-02-00' },

    {
        trigger: '.o_scan_message.o_scan_src',
        run: 'scan shelf3',
    },

    {
        trigger: '.o_barcode_location_line[data-location="WH/Stock/Section 3"].text-bg-800',
        run: 'scan product2',
    },

    {
        trigger: '.o_barcode_line.o_selected .qty-done:contains("1")',
        run: 'scan shelf4',
    },

    {
        trigger: '.o_scan_message.o_scan_validate',
        run: 'scan OBTPACK'
    },

    {
        trigger: '.modal .modal-title:contains("Choose destination location")',
        run: "click",
    },

    {
        trigger: '.modal .o_field_widget[name="location_dest_id"] input',
        run: 'click',
    },
    {
        isActive: ["auto"],
        trigger: '.modal .ui-menu-item > a:contains("Section 2")',
        run: "click",
    },

    {
        trigger: '.modal .o_field_widget[name="location_dest_id"]',
        run: function () {
            helper.assert(
                document.querySelector('.o_field_widget[name="location_dest_id"] input').value,
                'WH/Stock/Section 2'
            );
        },
    },

    {
        trigger: '.modal .btn-primary',
        run: "click",
    },
    {
        trigger: "body:not(:has(.modal))",
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_put_in_pack_scan_package', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(3);
        }
    },
    {
        trigger: '.o_scan_message.o_scan_src',
        run: 'scan LOC-01-01-00'
    },

    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan product1',
    },
    {
        trigger: '.o_barcode_line[data-barcode="product1"] .qty-done:contains("1")',
        run: 'scan OBTPACK',
    },
    {
        trigger: '.o_barcode_line:contains("product1"):contains("PACK0000001")',
        run: function() {
            const line1 = helper.getLine({ barcode: "product1", selected: true });
            const product1_package = line1.querySelector('div[name="package"]').innerText;
            helper.assert(product1_package, 'PACK0000001');
        }
    },

    // Scans product2 then scans the package.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2',
    },
    {
        trigger: '.o_barcode_line.o_highlight:contains("product2")',
        run: 'scan PACK0000001',
    },
    {
        trigger: '.o_barcode_line:contains("product2"):contains("PACK0000001")',
        run: function() {
            const line1 = helper.getLine({ barcode: "product1", completed: true });
            const line2 = helper.getLine({ barcode: "product2", selected: true });
            const product1_package = line1.querySelector('div[name="package"]').innerText;
            const product2_package = line2.querySelector('div[name="package"]').innerText;
            helper.assert(product1_package, 'PACK0000001');
            helper.assert(product2_package, 'PACK0000001');
        }
    },

    // Scans next location then scans again product1 and PACK0000001.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-02-00',
    },
    {
        trigger: '.o_barcode_location_line[data-location="WH/Stock/Section 2"].text-bg-800',
        run: 'scan product1',
    },
    {
        trigger: '.o_barcode_line[data-barcode="product1"].o_selected .qty-done:contains("1")',
        run: 'scan PACK0000001',
    },
    {
        trigger: '.o_barcode_line:contains("product1").o_selected:contains("PACK0000001")',
        run: function() {
            const line1 = helper.getLine({ barcode: "product1", selected: true });
            const product1_package = line1.querySelector('div[name="package"]').innerText;
            helper.assert(product1_package, 'PACK0000001');
        }
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_put_in_pack_new_lines', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan P00001',
    },
    {
        trigger: '.o_notification_bar.bg-danger',
        run: "click",
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1',
    },
    {
        trigger: '.o_barcode_line:contains("product1")',
        run: 'scan P00001',
    },
    {
        trigger: '.o_barcode_line:contains("product1"):contains("P00001")',
        run: 'scan OBTVALI',
    },
    {
        trigger: '.o_notification_bar.bg-success',
    },
]});

registry.category("web_tour.tours").add('test_picking_owner_scan_package', { steps: () => [
    {
        trigger: '.o_stock_barcode_main_menu',
        run: 'scan WHOUT',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan P00001',
    },
    { trigger: '.o_barcode_client_action:contains("P00001")' },
    { trigger: '.o_barcode_client_action:contains("Azure Interior")' },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_receipt_delete_button', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2',
    },
    ...stepUtils.confirmAddingUnreservedProduct(),
    // ensure receipt's extra product CAN be deleted
    {
        trigger: '.o_barcode_line[data-barcode="product2"] .o_edit',
        run: "click",
    },
    {
        trigger: '.o_field_widget[name="product_id"]',
        run: function () {
            helper.assert(document.querySelectorAll('.o_delete').length, 1);
        },
    },
    {
        trigger: '.o_discard',
        run: "click",
    },
    // ensure receipt's original move CANNOT be deleted
    {
        trigger: '.o_barcode_line:nth-child(2) .o_edit',
        run: "click",
    },
    {
        trigger: '.o_field_widget[name="product_id"]',
        run: function () {
            helper.assert(document.querySelectorAll('.o_delete').length, 0);
        },
    },
    {
        trigger: '.o_discard',
        run: "click",
    },
    // add extra product not in original move + delete it
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product3',
    },
    ...stepUtils.confirmAddingUnreservedProduct(),
    {
        trigger: '.o_barcode_line[data-barcode="product3"] .o_edit',
        run: "click",
    },
    {
        trigger: '.o_delete',
        run: "click",
    },
    {
        trigger: '.o_validate_page',
        run: 'scan OBTVALI',
    }, {
        content: "check the picking is validated",
        trigger: '.o_notification_bar.bg-success',
    },
]});

registry.category("web_tour.tours").add("test_scan_aggregate_barcode", { steps: () => [
    { trigger: '.o_stock_barcode_main_menu', run: 'scan WHIN' },
    // Scan 3x product1 (using ',' as separator).
    { trigger: '.o_barcode_client_action', run: 'scan product1,product1,product1' },
    {
        trigger: '.o_barcode_line.o_selected .qty-done:contains(3)',
        run: function () {
            helper.assertLinesCount(1);
            const line = helper.getLine({ barcode: 'product1' });
            helper.assertLineQty(line, "3");
        }
    },
    // Scan 1x product1 and 2x product2 (using '|' as separator).
    { trigger: '.o_barcode_client_action', run: 'scan product1|product2|product2' },
    {
        trigger: '.o_barcode_line.o_selected .qty-done:contains(2)',
        run: function () {
            helper.assertLinesCount(2);
            const notSelectedLine = helper.getLine({ selected: false });
            const selectedLine = helper.getLine({ selected: true });
            helper.assertLineProduct(notSelectedLine, "product1");
            helper.assertLineQty(notSelectedLine, "4");
            helper.assertLineProduct(selectedLine, "product2");
            helper.assertLineQty(selectedLine, "2");
        }
    },
    {
        content: "Scan a tracked product and all of its SNs",
        trigger: '.o_barcode_client_action',
        run: 'scan productserial1|sn01,sn02,sn05,sn04,sn03,sn06,sn10,sn07,sn08,sn09',
    },
    {
        trigger: '.o_barcode_line.o_selected .qty-done:contains(10)',
    },
    {
        content: "Unfold grouped lines (productserial1)",
        trigger: '.o_line_button.o_toggle_sublines',
        run: "click",
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add("test_scrap_change_source_location", { steps: () => [
    { trigger: ".o_barcode_actions", run: "click" },
    { trigger: "input#manual_barcode", run: "edit LOC-01-01-00" },
    { trigger: "button:contains('Apply')", run: "click" },
    { trigger: ".o_barcode_actions", run: "click" },
    { trigger: "input#manual_barcode", run: "edit Lot1" },
    { trigger: "button:contains('Apply')", run: "click" },
    { trigger: ".o_line_button:contains('+9')", run: "click" },
    { trigger: ".o_barcode_actions", run: "click" },
    { trigger: ".o_scrap", run: "click" },
    { trigger: "input#product_id_0", run: "edit product1" },
    { trigger: ".ui-menu-item > a:contains('product1')", run: "click" },
    { trigger: "input#scrap_qty_0", run: "edit 15" },
    { trigger: "input#location_id_0", run: "edit WH/Stock/Section 1" },
    { trigger: ".ui-menu-item > a:contains('WH/Stock/Section 1')", run: "click" },
    { trigger: "input#lot_id_0", run: "edit lot1" },
    { trigger: ".ui-menu-item > a:contains('lot1')", run: "click" },
    { trigger: "button.o_save", run: "click" },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add("test_scrap", { steps: () => [
    // Opens the receipt and checks we can't scrap if not done.
    { trigger: ".o_stock_barcode_main_menu", run: "scan receipt_scrap_test" },
    {
        trigger: ".o_barcode_actions",
        run: "click",
    },
    {
        trigger: ".o_barcode_settings",
        run: function() {
            const scrapButton = document.querySelector("button.o_scrap");
            helper.assert(Boolean(scrapButton), false, "Scrap button shouldn't be displayed");
        },
    },
    {
        trigger: "button.o_close",
        run: "click",
    },
    {
        trigger: ".o_barcode_lines",
        run: "scan OBTSCRA",
    },
    {
        trigger: ".o_notification:has(.o_notification_bar.bg-warning):contains('You can\\'t register scrap')",
        run: "click",
    },
    // Process the receipt then re-opens it again.
    {
        trigger: ".o_line_button.o_add_remaining_quantity",
        run: "click",
    },
    {
        trigger: ".o_validate_page.btn-primary",
        run: "click",
    },
    { trigger: ".o_stock_barcode_main_menu", run: "scan receipt_scrap_test" },
    {
        trigger: ".o_scan_message.o_picking_already_done",
        run: "scan OBTSCRA",
    },
    {
        trigger: ".o_field_widget[name='scrap_qty']",
    },
    {
        trigger: ".btn[special='cancel']",
        run: "click",
    },
    {
        trigger: ".o_barcode_actions",
        run: "click",
    },
    {
        trigger: ".o_barcode_settings",
        run: function() {
            const scrapButton = document.querySelector("button.o_scrap");
            helper.assert(Boolean(scrapButton), true, "Scrap button should be displayed");
        },
    },
    // Exits the receipt and opens the delivery.
    {
        trigger: "button.o_exit",
        run: "click",
    },
    {
        trigger: ".o_barcode_lines_header",
    },
    {
        trigger: "button.o_exit",
        run: "click",
    },
    { trigger: ".o_stock_barcode_main_menu", run: "scan delivery_scrap_test" },
    // Checks we can scrap for a delivery.
    {
        trigger: ".o_barcode_actions",
        run: "click",
    },
    {
        trigger: ".o_barcode_settings",
        run: function() {
            const scrapButton = document.querySelector("button.o_scrap");
            helper.assert(Boolean(scrapButton), true, "Scrap button should be displayed");
        },
    },
    {
        trigger: "button.o_close",
        run: "click",
    },
    { trigger: ".o_barcode_lines", run: "scan OBTSCRA" },
    {
        trigger: ".o_field_widget[name='scrap_qty']",
    },
    {
        trigger: ".btn[special='cancel']",
        run: "click",
    },
    // Process the delivery then re-opens it again.
    {
        trigger: ".o_line_button.o_add_remaining_quantity",
        run: "click",
    },
    {
        trigger: ".o_validate_page.btn-primary",
        run: "click",
    },
    { trigger: ".o_stock_barcode_main_menu", run: "scan delivery_scrap_test" },
    { trigger: ".o_barcode_lines_header", run: "scan OBTSCRA" },
    {
        trigger: ".o_notification:has(.o_notification_bar.bg-warning):contains('You can\\'t register scrap')",
        run: "click",
    },
    {
        trigger: ".o_barcode_actions",
        run: "click",
    },
    {
        trigger: ".o_barcode_settings",
        run: function() {
            const scrapButton = document.querySelector("button.o_scrap");
            helper.assert(Boolean(scrapButton), false, "Scrap button shouldn't be displayed");
        },
    },
    // Exits the delivery and opens the receipt, checks if the digipad scrap view is used
    {
        trigger: "button.o_exit",
        run: "click",
    },
    {
        trigger: ".o_barcode_lines_header",
    },
    {
        trigger: "button.o_exit",
        run: "click",
    },
    { trigger: ".o_stock_barcode_main_menu", run: "scan receipt_scrap_test" },
    {
        trigger: ".o_barcode_actions",
        run: "click",
    },
    {
        trigger: ".o_barcode_settings",
        run: "click",
    },
    {
        trigger: ".o_scrap",
        run: "click",
    },
    {
        trigger: ".o_qty_done_field_not_completed",
        run: function() {
            const digipadView = document.querySelector(".o_digipad_widget");
            helper.assert(Boolean(digipadView), true, "Scrap view should use the digipad widget.");
        },
    },
    {
        content: "Select SN product from the dropdown",
        trigger: ".o_input_dropdown .o_input#product_id_0",
        run: "click",
    },
    {
        content: "Product `productserial1` should be available, despite not having any move lines",
        trigger: "a.dropdown-item:contains('productserial1')",
        run: "click",
    },
    {
        content: "Digipad should be hidden after selecting the SN product",
        trigger: "body:not(:has(.o_digipad_widget))",
    },
    {
        content: "Check available lots",
        trigger: ".o_input_dropdown .o_input#lot_id_0",
        run: "click",
    },
    {
        trigger: "ul.o-autocomplete--dropdown-menu",
    },
    {
        trigger: "a.dropdown-item:contains('SN')",
        run: function() {
            const dropdownContent = document.querySelector(".dropdown-menu").textContent;
            helper.assert(
                dropdownContent.includes("SN0001") && dropdownContent.includes("SN0002"), true,
                "All SN lots for productserial1 should be available in the dropdown."
            );
        },
    },
    {
        trigger: "input#should_replenish_0",
        run: "click",
    },
    // Exits the form
    {
        trigger: "button.o_discard",
        run: "click",
    },
    {
        trigger: "button.o_exit",
        run: "click",
    },
    {
        trigger: 'button.o_button_operations',
    },
]});

registry.category("web_tour.tours").add("test_picking_scan_package_confirmation", { steps: () => [
    // Scan product 1
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    // Scan Package 1 to trigger the scan confirmation
    { trigger: '.o_barcode_line .qty-done:contains("1")', run: 'scan package001' },
    // Cancel the package scan
    {
        trigger: ".modal-content button.btn-secondary",
        run: "click",
    },
    // Scan Package 1 to trigger the scan confirmation
    { trigger: '.o_barcode_line .qty-done:contains("1")', run: 'scan package001' },
    // Confirm the package scan, thus the line quantity will be increased
    {
        trigger: ".modal-content button.btn-primary",
        run: "click",
    },
    { trigger: '.o_barcode_line .qty-done:contains("2")'},
]});

registry.category("web_tour.tours").add('test_show_entire_package', { steps: () => [
    {
        trigger: 'button.o_button_operations',
        run: "click",
    },
    {
        trigger: '.o_kanban_record:contains(Delivery Orders)',
        run: "click",
    },

    // Opens picking with the package level.
    {
        trigger: '.o_kanban_record:contains(Delivery with Package Level)',
        run: "click",
    },
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertLinesCount(1);
            helper.assertScanMessage('scan_product_or_package');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
            const line = helper.getLine();
            helper.assertLineIsHighlighted(line, false);
            helper.assertButtonIsVisible(line, "package_content");
            helper.assertButtonIsVisible(line, "add_remaining_quantity", false);
            helper.assert(line.querySelector('[name="package"]').innerText, "package001package001");
            helper.assertLineQty(line, "0/1");
        },
    },
    {
        trigger: '.o_line_button.o_package_content',
        run: "click",
    },
    {
        trigger: '.o_kanban_view .o_kanban_record',
        run: function () {
            helper.assertKanbanRecordsCount(1);
        },
    },
    {
        trigger: 'button.o_close',
        run: "click",
    },
    // Scan the unreserved package002 and remove it as it was a mistake
    { trigger: '.o_barcode_lines', run: 'scan package002' },
    {
        trigger: '.o_barcode_line[data-package=package002]',
        run: function () {
            helper.assertLinesCount(2);
            const [line1, line2] = helper.getLines();
            helper.assert(line1.querySelector("[name=package]").innerText, "package001package001");
            helper.assertLineQty(line1, "0/1");
            helper.assertLineIsFaulty(line1, false)
            helper.assert(line2.querySelector("[name=package]").innerText, "package002package002");
            helper.assertLineQty(line2, "1");
            helper.assertLineIsFaulty(line2, true)
        },
    },
    {
        trigger: '.o_barcode_line[data-package=package002] .o_delete_line',
        run: 'click',
    },
    {
        trigger: '.o_barcode_lines:not(:has(.o_delete_line))'
    },
    // Scans package001 to be sure no moves will be created but the package line will be done.
    { trigger: '.o_barcode_lines', run: 'scan package001' },
    {
        trigger: '.o_barcode_line.o_line_completed',
        run: function () {
            helper.assertLinesCount(1);
            helper.assertScanMessage('scan_validate');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(true);
            helper.assertValidateEnabled(true);
            const line = helper.getLine();
            helper.assertLineIsHighlighted(line, false);
            helper.assertButtonIsVisible(line, "package_content");
            helper.assert(line.querySelector('[name="package"]').innerText, "package001package001");
            helper.assertLineQty(line, "1/1");
        },
    },
    {
        trigger: 'button.o_exit',
        run: "click",
    },

    // Opens picking with the move.
    {
        trigger: '.o_kanban_record:contains(Delivery with Stock Move)',
        run: "click",
    },
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertLinesCount(1);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
            const line = helper.getLine();
            helper.assertLineIsHighlighted(line, false);
            helper.assertButtonIsVisible(line, "package_content", false);
            helper.assert(line.querySelector('[name="package"]').innerText, "package002");
            helper.assertLineQty(0, '0/2');
        },
    },
]});

registry.category("web_tour.tours").add('test_define_the_destination_package', { steps: () => [
    {
        trigger: '.o_line_button.o_add_remaining_quantity',
        run: "click",
    },
    {
        trigger: '.o_barcode_line .qty-done:contains("1")',
        run: 'scan PACK02',
    },
    {
        trigger: '.o_barcode_line:contains("PACK02")',
    },
    {
        trigger: '.btn.o_validate_page',
        run: "click",
    },
    {
        trigger: '.o_notification_bar.bg-success',
    },
]});

registry.category("web_tour.tours").add('stock_barcode_package_with_lot', { steps: () => [
    {
        trigger: "[data-menu-xmlid='stock_barcode.stock_barcode_menu']", // open barcode app
        run: "click",
    },
    {
        trigger: ".o_button_inventory",
        run: "click",
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan Lot-test' // scan lot on a new location
    },
    {
        trigger: '.o_barcode_line .package:contains(Package-test)', // verify it takes the right quantity
    },
    {
        trigger: '.o_apply_page',
        run: "click",
    },
    {
        trigger: '.o_notification_bar.bg-success',
    },
]});

registry.category("web_tour.tours").add('test_scan_same_lot_different_products', { steps: () => [
    // Scanning 123 will fetch the lot 123 for the 'aaa' product and add them
    // both in the cache (the 'aaa' product and its lot.)
    {
        trigger: '.o_barcode_client_action',
        run: 'scan 123',
    },
    {
        trigger: '.o_notification_bar.bg-danger',
        run: 'scan bbb',
    },
    // Scanning again 123 should now fetch the lot for selected product ('bbb')
    // even if the lot 123 for 'aaa' product is already in the cache.
    {
        trigger: '.o_barcode_line:contains("bbb")',
        run: 'scan 123',
    },
    {
        trigger: '.o_barcode_line:contains("bbb"):contains("123")',
        run: function () {
            helper.assertLinesCount(1);
        },
    },
]});

registry.category("web_tour.tours").add('test_avoid_useless_line_creation', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOT01',
    },
    {
        trigger: '.o_barcode_line',
        run: 'scan LOREM',
    },
    {
        trigger: '.o_notification_bar.bg-danger',
        run: function () {
            helper.assertErrorMessage("This product doesn't exist.");
        },
    },
    // Open the form view to trigger a save
    {
        trigger: '.o_barcode_line:first-child .o_edit',
        run: "click",
    },
    ...stepUtils.discardBarcodeForm(),
]});

registry.category("web_tour.tours").add('test_setting_barcode_allow_extra_product', { steps: () => [
    // Scans the delivery to open it.
    { trigger: '.o_stock_barcode_main_menu', run: 'scan delivery_test' },
    // Scans the reserved product.
    { trigger: '.o_barcode_line', run: 'scan product1' },
    // Try to scan a not-reserved product -> Display a warning.
    { trigger: '.o_barcode_line.o_selected.o_line_completed', run: 'scan product2' },
    {
        trigger: '.o_notification_bar.bg-danger',
        run: function() {
            helper.assertErrorMessage("The product product2 should not be picked in this operation.");
        }
    },
    // Valid the delivery, then create another one. Checks any product can be scanned regardless the delivery type config.
    { trigger: '.o_barcode_client_action', run: 'scan OBTVALI' },
    { trigger: '.o_stock_barcode_main_menu', run: 'scan WHOUT' },
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    { trigger: '.o_barcode_line', run: 'scan product2' },
    { trigger: '.o_barcode_line:nth-child(2)', run: function() {
        const lines = helper.getLines();
        helper.assert(lines.length, 2);
        helper.assertLineProduct(lines[0], "product1");
        helper.assertLineProduct(lines[1], "product2");
    }},
]});

registry.category("web_tour.tours").add("test_setting_barcode_allow_extra_product_with_packages", {
    steps: () => [
        {
            trigger: ".o_stock_barcode_main_menu",
            run: "scan SBAEPWP",
        },
        // Scan package with extra product -> ignored + raise notification
        {
            trigger: ".o_barcode_client_action",
            run: "scan PACK04",
        },
        {
            trigger: '.o_notification_bar.bg-danger',
            run: function () {
                helper.assertErrorMessage("This package contains extra products and extra products are not allowed on this operation.");
            },
        },
        // Scan valid package -> should be processed
        {
            trigger: ".o_barcode_client_action",
            run: "scan PACK01",
        },
        {
            trigger: ".o_barcode_line:contains(PACK01)",
            run: () => {
                helper.assertLinesCount(2);
                const [line1, line2] = helper.getLines();
                helper.assertLineQty(line1, "0/5");
                helper.assertLineQty(line2, "10");
            }
        },
        {
            trigger: "button.o_exit",
            run: "click"
        },
        // process the move entire packages delivery
        {
            trigger: ".o_stock_barcode_main_menu",
            run: "scan SBAEPWMEP",
        },
        // Scan package with extra product -> ignored + raise notification
        {
            trigger: ".o_barcode_client_action",
            run: "scan PACK04",
        },
        {
            trigger: '.o_notification_bar.bg-danger',
            run: function () {
                helper.assertErrorMessage("This package contains extra products and extra products are not allowed on this operation.");
            },
        },
        // Scan valid package -> should be processed
        {
            trigger: ".o_barcode_client_action",
            run: "scan PACK03",
        },
        {
            trigger: ".o_barcode_line[data-package=PACK03]",
            run: () => {
                helper.assertLinesCount(2);
                const [line1, line2] = helper.getLines();
                helper.assert(line1.querySelector("[name=package]").innerText, "PACK02PACK02")
                helper.assert(line2.querySelector("[name=package]").innerText, "PACK03PACK03")
            }
        },
    ],
});

registry.category("web_tour.tours").add('test_split_line_reservation', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertLinesCount(3);
            helper.assertScanMessage('scan_src');
        },
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-00-00'
    },
    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan productlot1'
    },
    {
        trigger: '.o_scan_message.o_scan_lot',
        run: 'scan LOT01'
    },
    {
        trigger: '.o_scan_message.o_scan_lot',
        run: 'scan LOT02'
    },
    {
        trigger: '.o_barcode_line.o_selected .qty-done:contains(2)',
        run: 'scan LOC-01-01-00'
    },
    {
        trigger: '.o_barcode_location_line[data-location="WH/Stock/Section 1"].text-bg-800',
        run: function () {
            helper.assertLinesCount(4);
            let line = helper.getLine({ barcode: 'productlot1', completed: true });
            helper.assertLineSourceLocation(line, 'WH/Stock');
            helper.assertLineQty(line, '2/2');
            line = helper.getLine({ barcode: 'productlot1', completed: false });
            helper.assertLineSourceLocation(line, 'WH/Stock/Section 1');
            helper.assertLineQty(line, '0/3');
        },
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan productlot1'
    },
    {
        trigger: '.o_barcode_line.o_selected',
        run: 'scan LOT02'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOT02'
    },
    {
        trigger: '.o_barcode_line.o_selected .qty-done:contains(2)',
        run: 'scan LOC-01-02-00'
    },
    {
        trigger: '.o_barcode_location_line[data-location="WH/Stock/Section 2"].text-bg-800',
        run: function () {
            helper.assertLinesCount(5);
        },
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan productlot1'
    },
    {
        trigger: '.o_barcode_line.o_selected',
        run: 'scan LOT03'
    },
    {
        trigger: '.o_barcode_line .o_line_lot_name:contains("LOT03")',
        run: function () {
            const lines = helper.getLines({ barcode: 'productlot1' });
            [0, 1, 2].map(i => helper.assertLineQty(lines[i], ["2/2", "2/2", "1/1"][i]));
        },
    },
    // Scan product1 x2 from WH/Stock.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-00-00'
    },
    {
        trigger: '.o_barcode_location_line.text-bg-800[data-location="WH/Stock"]',
        run: 'scan product1'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },
    {
        trigger: '.o_barcode_line.o_selected .qty-done:contains(2)',
        run: 'scan LOC-01-01-00'
    },
    {
        trigger: '.o_barcode_line[data-barcode="product1"].o_line_completed',
        run: function () {
            helper.assertLinesCount(6);
            const lines = helper.getLines({ barcode: 'product1' });
            [0, 1].map(i => helper.assertLineQty(lines[i], ["2/2", "0/2"][i]));
        },
    },
    // scan product1 x2 from Section 1
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },
    {
        trigger: '.o_barcode_line.o_selected:not(.o_line_completed)',
        run: 'scan product1'
    },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: 'scan LOC-01-00-00'
    },
    // scan product2 x2 from WH/Stock
    {
        trigger: '.o_barcode_location_line.text-bg-800[data-location="WH/Stock"]',
        run: 'scan product2'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2'
    },
    {
        trigger: '.o_barcode_line.o_selected .qty-done:contains(2)',
        run: 'scan LOC-01-01-00'
    },
    {
        trigger: '.o_barcode_line[data-barcode="product2"].o_line_completed',
        run: function () {
            helper.assertLinesCount(7);
            const lines = helper.getLines({ barcode: 'product2' });
            [0, 1].map(i => helper.assertLineQty(lines[i], ["2/2", "0/1"][i]));
        },
    },
    // scan product2 x1 from Section 1
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2'
    },
    { trigger: ".o_validate_page.btn-primary"},
    // Open a line form view to trigger a save.
    { trigger: '.o_barcode_line .o_edit', run: "click" },
    { trigger: '.o_discard', run: "click" },
    {
        trigger: '.o_barcode_line',
        run: function () {
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(true);
            helper.assertValidateEnabled(true);
            // Check lines' quantity didn't change.
            let lines = helper.getLines({ barcode: 'product1' });
            [0, 1].map(i => helper.assertLineQty(lines[i], ["2/2", "2/2"][i]));
            lines = helper.getLines({ barcode: 'product2' });
            [0, 1].map(i => helper.assertLineQty(lines[i], ["2/2", "1/1"][i]));
            lines = helper.getLines({ barcode: 'productlot1' });
            [0, 1, 2].map(i => helper.assertLineQty(lines[i], ["2/2", "2/2", "1/1"][i]));
        },
    },
]});

registry.category("web_tour.tours").add('test_split_line_on_destination_scan', { steps: () => [
    // Open the receipt then scans 2x product1.
    { trigger: '.o_stock_barcode_main_menu', run: "scan receipt_split_line_on_destination_scan" },
    { trigger: '.o_barcode_line', run: "scan product1" },
    { trigger: '.o_barcode_line', run: "scan product1" },
    {
        trigger: '.o_barcode_line.o_selected .qty-done:contains("2")',
        run: () => {
            helper.assertLinesCount(1);
            helper.assertLineDestinationLocation(0, "WH/Stock");
            helper.assertLineQty(0, "2/4");
        }
    },
    // Scans the line's destination -> The line should be splitted in two.
    { trigger: '.o_barcode_line', run: "scan LOC-01-00-00" },
    {
        trigger: '.o_barcode_line:nth-child(2)',
        run: () => {
            helper.assertLinesCount(2);
            helper.assertLineDestinationLocation(0, "WH/Stock");
            helper.assertLineDestinationLocation(1, "WH/Stock");
            helper.assertLineQty(0, "2/2");
            helper.assertLineQty(1, "0/2");
        }
    },
    // Scans remaining quantity, then shelf1 as the destination and close the receipt.
    { trigger: '.o_barcode_line', run: "scan product1" },
    { trigger: '.o_barcode_line.o_selected:not(.o_line_completed)', run: "scan product1" },
    { trigger: '.o_barcode_line.o_selected.o_line_completed', run: "scan LOC-01-01-00" },
    {
        trigger: '.o_line_destination_location:contains(".../Section 1")',
        run: () => {
            helper.assertLinesCount(2);
            helper.assertLineDestinationLocation(0, "WH/Stock");
            helper.assertLineDestinationLocation(1, ".../Section 1");
            helper.assertLineQty(0, "2/2");
            helper.assertLineQty(1, "2/2");
        }
    },
    ...stepUtils.validateBarcodeOperation(),
    // Now, open the internal transfer and scan Section 1 as the source location.
    { trigger: '.o_stock_barcode_main_menu', run: "scan internal_split_line_on_destination_scan" },
    {
        trigger: '.o_barcode_line',
        run: () => {
            helper.assertLinesCount(2);
            helper.assertLineLocations(0, "WH/Stock/Section 1", "WH/Stock");
            helper.assertLineQty(0, "0/3");
            helper.assertLineLocations(1, "WH/Stock/Section 2", "WH/Stock");
            helper.assertLineQty(1, "0/4");
        }
    },
    { trigger: '.o_scan_message.o_scan_src', run: "scan LOC-01-01-00" },
    // Scan 2x product2 then scan Section 3 as the destination.
    { trigger: '.o_barcode_line', run: "scan product2" },
    { trigger: '.o_barcode_line', run: "scan product2" },
    { trigger: '.o_barcode_line.o_selected .qty-done:contains("2")', run: "scan shelf3" },
    {
        trigger: '.o_scan_message.o_scan_src',
        run: () => {
            helper.assertLinesCount(3);
            helper.assertLineLocations(0, "WH/Stock/Section 1", ".../Section 3");
            helper.assertLineQty(0, "2/2");
            helper.assertLineLocations(1, "WH/Stock/Section 1", "WH/Stock");
            helper.assertLineQty(1, "0/1");
            helper.assertLineLocations(2, "WH/Stock/Section 2", "WH/Stock");
            helper.assertLineQty(2, "0/4");
        }
    },
    // Scan 1x product2 then scan WH/Stock as the destination.
    { trigger: '.o_barcode_line', run: "scan LOC-01-01-00" },
    { trigger: '.o_scan_message.o_scan_product', run: "scan product2" },
    { trigger: '.o_barcode_line.o_selected.o_line_completed', run: "scan LOC-01-00-00" },
    {
        trigger: '.o_scan_message.o_scan_src',
        run: () => {
            helper.assertLinesCount(3);
            helper.assertLineLocations(0, "WH/Stock/Section 1", ".../Section 3");
            helper.assertLineQty(0, "2/2");
            helper.assertLineLocations(1, "WH/Stock/Section 1", "WH/Stock");
            helper.assertLineQty(1, "1/1");
            helper.assertLineLocations(2, "WH/Stock/Section 2", "WH/Stock");
            helper.assertLineQty(2, "0/4");
        }
    },
    // Scan Section 2 as the source and then 2x product2.
    { trigger: '.o_barcode_line', run: "scan LOC-01-02-00" },
    { trigger: '.o_scan_message.o_scan_product', run: "scan product2" },
    { trigger: '.o_scan_message.o_scan_product_or_dest', run: "scan product2" },
    // Now scan Section 2 also as the destination.
    { trigger: '.o_barcode_line.o_selected .qty-done:contains("2")', run: "scan LOC-01-02-00" },
    {
        trigger: '.o_scan_message.o_scan_src',
        run: () => {
            helper.assertLinesCount(4);
            helper.assertLineLocations(0, "WH/Stock/Section 1", ".../Section 3");
            helper.assertLineQty(0, "2/2");
            helper.assertLineLocations(1, "WH/Stock/Section 1", "WH/Stock");
            helper.assertLineQty(1, "1/1");
            helper.assertLineLocations(2, "WH/Stock/Section 2", ".../Section 2");
            helper.assertLineQty(2, "2/2");
            helper.assertLineLocations(3, "WH/Stock/Section 2", "WH/Stock");
            helper.assertLineQty(3, "0/2");
        }
    },
    // Scan 2x product2, Section 1 as the destination and close the internal transfer.
    { trigger: '.o_scan_message.o_scan_src', run: "scan LOC-01-02-00" },
    { trigger: '.o_scan_message.o_scan_product', run: "scan product2" },
    { trigger: '.o_scan_message.o_scan_product_or_dest', run: "scan product2" },
    { trigger: '.o_scan_message.o_scan_dest', run: "scan LOC-01-01-00" },
    ...stepUtils.validateBarcodeOperation('.o_validate_page.btn-primary'),
]});

registry.category("web_tour.tours").add('test_split_line_on_exit_for_delivery', { steps: () => [
    // Opens the delivery and checks its lines.
    { trigger: ".o_stock_barcode_main_menu", run: "scan delivery_split_line_on_exit" },
    {
        trigger: ".o_barcode_client_action",
        run: () => {
            helper.assertLinesCount(3);
            helper.assertLineProduct(0, "product1");
            helper.assertLineQty(0, "0/4");
            helper.assertLineProduct(1, "product2");
            helper.assertLineQty(1, "0/4");
            helper.assertLineProduct(2, "product3");
            helper.assertLineQty(2, "0/2");
        }
    },
    // Scans 4x product1, 2x product2 and leaves the delivery without scanning product3.
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    { trigger: ".o_barcode_line.o_selected.o_line_completed", run: "scan product2" },
    { trigger: ".o_barcode_line.o_selected:not(.o_line_completed)", run: "scan product2" },
    // Leaves the delivery, the 2/4 product2 line should be split into two lines (2/2 and 0/2.)
    { trigger: ".o_barcode_line.o_selected .qty-done:contains(2)"},
    { trigger: "button.o_exit", run: "click" },
    { trigger: ".o_stock_barcode_main_menu" },
]});

registry.category("web_tour.tours").add("test_split_uncomplete_moves_on_exit_with_neutral_changes", {
    steps: () => [
        {
            trigger: ".o_stock_barcode_main_menu",
            run: "scan SUMOEWNC"
        },
        {
            trigger: ".o_barcode_line .o_toggle_sublines",
            run: "click",
        },
        {
            trigger: ".o_barcode_line",
            run: () => {
                helper.assertLinesCount(1);
                helper.assertLineQty(0, "0/4");
                const [ subLine1, subLine2 ] = helper.getSublines();
                helper.assert(subLine1.querySelector(".o_line_lot_name").innerText, "LN001");
                helper.assertLineQty(subLine1, "0/2");
                helper.assert(subLine2.querySelector(".o_line_lot_name").innerText, "LN002");
                helper.assertLineQty(subLine2, "0/2");
            }
        },
        // Scans SN01 and remove it
        { trigger: ".o_barcode_client_action", run: "scan LN001" },
        { trigger: ".o_barcode_client_action", run: "scan LN001" },
        {
            trigger: ".o_barcode_line.o_line_completed .o_edit",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='qty_done'] input",
            run: "edit 0",
        },
        {
            trigger: ".o_save",
            run: "click",
        },
        {
            trigger: ".o_barcode_line",
            run: () => {
                helper.assertLinesCount(1);
                helper.assertLineQty(0, "0/4");
                const [ subLine1, subLine2 ] = helper.getSublines();
                helper.assert(subLine1.querySelector(".o_line_lot_name").innerText, "LN001");
                helper.assertLineQty(subLine1, "0/2");
                helper.assert(subLine2.querySelector(".o_line_lot_name").innerText, "LN002");
                helper.assertLineQty(subLine2, "0/2");
            }
        },
        // Leave and re-open the picking it directly
        { trigger: "button.o_exit", run: "click" },
        { trigger: ".o_stock_barcode_main_menu", run: "scan SUMOEWNC" },
        {
            trigger: ".o_barcode_line .o_toggle_sublines",
            run: "click",
        },
        {
            trigger: ".o_barcode_line",
            run: () => {
                helper.assertLinesCount(1);
                helper.assertLineQty(0, "0/4");
                const [ subLine1, subLine2 ] = helper.getSublines();
                helper.assert(subLine1.querySelector(".o_line_lot_name").innerText, "LN002");
                helper.assertLineQty(subLine1, "0/2");
                helper.assert(subLine2.querySelector(".o_line_lot_name").innerText, "LN001");
                helper.assertLineQty(subLine2, "0/2");
            }
        },
    ]
});

registry.category("web_tour.tours").add('test_split_line_on_exit_for_receipt', { steps: () => [
    // Opens the receipt and check its lines.
    { trigger: ".o_stock_barcode_main_menu", run: "scan receipt_split_line_on_exit" },
    {
        trigger: ".o_barcode_client_action",
        run: () => {
            helper.assertLinesCount(2);
            helper.assertLineProduct(0, "product1");
            helper.assertLineQty(0, "0/4");
            helper.assertLineProduct(1, "product2");
            helper.assertLineQty(1, "0/4");
        }
    },
    // Scans 1x product1 then put in pack => Should split the line.
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    { trigger: ".o_barcode_line.o_selected", run: "scan OBTPACK" },
    // Scans again 2x product1 => The line with no package just be incremented.
    { trigger: ".o_barcode_line.o_selected .result-package", run: "scan product1" },
    { trigger: ".o_barcode_line.o_selected.o_line_not_completed", run: "scan product1" },
    // Scans 1x product2 then checks the lines' state.
    { trigger: ".o_barcode_line.o_selected .qty-done:contains('2')", run: "scan product2" },
    {
        trigger: ".o_barcode_line.o_selected .qty-done:contains('1')",
        run: () => {
            helper.assertLinesCount(3);
            const [line1, line2, line3] = helper.getLines();
            helper.assertLineProduct(line1, "product1");
            helper.assertLineQty(line1, "2/3");
            helper.assertLineProduct(line2, "product2");
            helper.assertLineQty(line2, "1/4");
            helper.assertLineProduct(line3, "product1");
            helper.assertLineQty(line3, "1/1");
            helper.assert(line3.querySelector(".result-package").innerText, "PACK0001000")
        }
    },
    // Goes back to the main menu (that's here the uncompleted lines shoud be split.)
    {
        trigger: "button.o_exit",
        run: "click",
    },
    // Re-opens the picking and checks uncompleted lines were split.
    { trigger: ".o_stock_barcode_main_menu", run: "scan receipt_split_line_on_exit" },
    {
        trigger: ".o_barcode_client_action",
        run: () => {
            helper.assertLinesCount(5);
            const [line1, line2, line3, line4, line5] = helper.getLines();
            helper.assertLineProduct(line1, "product1");
            helper.assertLineQty(line1, "0/1");
            helper.assertLineProduct(line2, "product2");
            helper.assertLineQty(line2, "0/3");
            helper.assertLineProduct(line3, "product1");
            helper.assertLineQty(line3, "2/2");
            helper.assertLineProduct(line4, "product1");
            helper.assertLineQty(line4, "1/1");
            helper.assert(line4.querySelector(".result-package").innerText, "PACK0001000")
            helper.assertLineProduct(line5, "product2");
            helper.assertLineQty(line5, "1/1");
        }
    },
]});

registry.category("web_tour.tours").add("test_split_line_on_exit_for_delivery_with_lot", { steps: () => [
    // Opens the delivery and checks its lines.
    { trigger: ".o_stock_barcode_main_menu", run: "scan delivery_split_move_on_exit" },
    {
        trigger: ".o_barcode_client_action",
        run: () => {
            helper.assertLinesCount(1);
            helper.assertLineProduct(0, "productlot1");
            helper.assertLineQty(0, "0/3");
        }
    },
    // Scans 3x productlot1: 2x LOT002 and 1x LOT001.
    { trigger: ".o_barcode_client_action", run: "scan productlot1" },
    { trigger: ".o_barcode_line.o_selected", run: "scan LOT002" },
    { trigger: ".o_barcode_line.o_selected", run: "scan LOT002" },
    { trigger: ".o_barcode_line.o_selected", run: "scan LOT001" },
    {
        trigger: ".o_barcode_line.o_selected.o_line_completed  .o_line_button.o_toggle_sublines",
        run: "click",
    },
    {
        trigger: ".o_barcode_line_details .o_line_lot_name:contains(LOT001)",
        run: () => {
            helper.assertLinesCount(1);
            helper.assertLineQty(0, "3/3");
            const [lot002Line, lot001Line] = helper.getSublines();
            helper.assertLineTrackingNumber(lot002Line, "LOT002");
            helper.assertLineQty(lot002Line, "2");
            helper.assertLineTrackingNumber(lot001Line, "LOT001");
            helper.assertLineQty(lot001Line, "1");
        }
    },
    // Leaves the delivery and re-open it directly, then checks not lines were splitted.
    { trigger: "button.o_exit", run: "click" },
    { trigger: ".o_stock_barcode_main_menu", run: "scan delivery_split_move_on_exit" },
    {
        trigger: ".o_barcode_line.o_line_completed  .o_line_button.o_toggle_sublines",
        run: "click",
    },
    {
        trigger: ".o_barcode_line_details .o_line_lot_name:contains(LOT001)",
        run: () => {
            helper.assertLinesCount(1);
            helper.assertLineQty(0, "3/3");
            const [lot002Line, lot001Line] = helper.getSublines();
            helper.assertLineTrackingNumber(lot002Line, "LOT002");
            helper.assertLineQty(lot002Line, "2");
            helper.assertLineTrackingNumber(lot001Line, "LOT001");
            helper.assertLineQty(lot001Line, "1");
        }
    },
    { trigger: "button.o_exit", run: "click" },
    { trigger: ".o_stock_barcode_main_menu", run(){} },
]});

registry.category("web_tour.tours").add("test_split_line_on_exit_for_receipt_with_grouped_lot", {
    steps: () => [
        // Opens the receipt and checks its lines.
        { trigger: ".o_stock_barcode_main_menu", run: "scan SPLOEFRWGL" },
        {
            trigger: ".o_barcode_client_action",
            run: () => {
                helper.assertLinesCount(1);
                helper.assertLineProduct(0, "productlot1");
                helper.assertLineQty(0, "0/3");
            }
        },
        // Add one unit
        {
            trigger: ".o_edit .fa-pencil",
            run: "click",
        },
        {
            trigger: ".o_digipad_increment",
            run: "click",
        },
        {
            trigger: '.o_save',
            run: "click",
        },
        {
            trigger: ".o_barcode_line_details",
            run: () => {
                helper.assertLinesCount(1);
                helper.assertLineQty(0, "1/3");
            }
        },
        // Leaves the receipt and re-open it directly, the line was not splitted.
        { trigger: "button.o_exit", run: "click" },
        { trigger: ".o_stock_barcode_main_menu", run: "scan SPLOEFRWGL" },
        {
            trigger: ".o_barcode_line_details",
            run: () => {
                helper.assertLinesCount(1);
                helper.assertLineQty(0, "1/3");
            }
        },
        // Add the remaining quantity and leave
        {
            trigger: ".o_add_remaining_quantity",
            run: "click",
        },
        {
            trigger: ".o_barcode_line .qty-done:contains(3)",
            run: () => {
                helper.assertLinesCount(1);
                helper.assertLineQty(0, "3/3");
            }
        },
        { trigger: "button.o_exit", run: "click" },
        { trigger: ".o_stock_barcode_main_menu", run: "scan SPLOEFRWGL" },
        {
            trigger: ".o_barcode_line .qty-done:contains(3)",
            run: () => {
                helper.assertLinesCount(1);
                helper.assertLineQty(0, "3/3");
            }
        },
    ],
});

registry.category("web_tour.tours").add('test_split_line_on_scan', { steps: () => [
    // Scan product2 twice
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2'
    },
    {
        trigger: '.o_barcode_line.o_selected .qty-done:contains(1)',
        run: 'scan product2'
    },
    // Add current balance to empty pack
    {
        trigger:  '.o_barcode_line.o_selected .qty-done:contains(2)',
        run: 'scan THEPACK1'
    },
    // Check that line gets split properly
    {
        trigger: '.o_barcode_line[data-barcode="product2"].o_line_completed',
        run: function () {
            helper.assertLinesCount(2);
            [0, 1].map(i => helper.assertLineQty(i, ["0/3", "2/2"][i]));
        },
    },
    // Assign empty move line to other empty pack
    {
        trigger: '.o_barcode_client_action',
        run: 'scan THEPACK2'
    },
    // Ensure it doesn't split prematurely
    {
        trigger:  '.o_barcode_line.o_selected:contains("THEPACK2") .qty-done:contains(0)',
        run: function () {
            helper.assertLinesCount(2);
            const lines = helper.getLines({ barcode: 'product2' });
            helper.assert(lines[0].querySelector('.result-package').innerText, "THEPACK2");
            helper.assert(lines[1].querySelector('.result-package').innerText, "THEPACK1");
        },
    },
    // Add product2 x3 to finish the new move line
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2'
    },
    {
        trigger: '.o_validate_page',
        run: function () {
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(true);
            helper.assertValidateEnabled(true);
            // Check that lines' quantity didn't change.
            helper.assertLinesCount(2);
            [0, 1].map(i => helper.assertLineQty(i, ["3/3", "2/2"][i]));
        },
    },
    {
        trigger: '.btn.o_validate_page',
        run: "click",
    },
    { trigger: '.o_notification_bar.bg-success'},
]});

registry.category("web_tour.tours").add('test_scan_line_splitting_preserve_destination', { steps: () => [
    // Select the first (only) line
    {
        trigger: '.o_barcode_line',
        run: 'click',
    },
    {
        trigger:  '.o_barcode_line.o_selected',
        run: function () {
            helper.assertLinesCount(1);
            helper.assertLineQty(0, '0/5');
            helper.assertLineDestinationLocation(0, 'WH/Stock');
        },
    },
    // Reassign destination, add product2 x3, then pack it
    {
        trigger: '.o_barcode_line',
        run: 'scan shelf3',
    },
    {
        trigger: '.o_barcode_line .o_line_destination_location:contains("Section 3")',
        run: 'scan product2',
    },
    {
        trigger: '.o_barcode_line',
        run: 'scan product2',
    },
    {
        trigger: '.o_barcode_line .qty-done:contains("2")',
        run: 'scan THEPACK1',
    },
    // Ensure that packing split the line and preserved the new destination
    {
        trigger:  '.o_barcode_line.o_selected .qty-done:contains(0)',
        run: function () {
            helper.assertLinesCount(2);
            [0, 1].map(i => helper.assertLineQty(i, ["0/3", "2/2"][i]));
            [0, 1].map(i => helper.assertLineDestinationLocation(i, '.../Section 3'));
        },
    },
    // Add product2 x3, completing the remaining line, then add to a pack, then reassign destination
    {
        trigger: '.o_barcode_line',
        run: 'scan product2',
    },
    {
        trigger: '.o_barcode_line',
        run: 'scan product2',
    },
    {
        trigger: '.o_barcode_line',
        run: 'scan product2',
    },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: 'scan THEPACK2',
    },
    {
        trigger: '.o_barcode_line.o_selected .result-package:contains("THEPACK2")',
        run: 'scan shelf4',
    },
    {
        trigger: '.o_barcode_line .o_line_destination_location:contains("Section 4")',
        run: function () {
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(true);
            helper.assertValidateEnabled(true);
            // Check that lines' quantity didn't change.
            helper.assertLinesCount(2);
            const lines = helper.getLines({ barcode: 'product2' });
            [0, 1].map(i => helper.assert(lines[i].querySelector('.result-package').innerText, ["THEPACK2","THEPACK1"][i]));
            [0, 1].map(i => helper.assertLineQty(lines[i], ["3/3", "2/2"][i]));
            [0, 1].map(i => helper.assertLineDestinationLocation(lines[i], [".../Section 4", ".../Section 3"][i]));
        },
    },
    {
        trigger: '.btn.o_validate_page',
        run: "click",
    },
    { trigger: '.o_notification_bar.bg-success'},
]});

registry.category("web_tour.tours").add("test_split_line_preserve_package", { steps: () => [
    {
        trigger:  ".o_barcode_line",
        run: function () {
            helper.assertLinesCount(1);
            helper.assertLineQty(0, "0/50");
            helper.assertLinePackage(0, "THEPACK1");
        },
    },
    {
        trigger: ".o_barcode_line .o_edit",
        run: "click",
    },
    {
        trigger: "div[name=qty_done] input",
        run() {
            //input type number not supported by tour helpers.
            // It would work if the clipboard was mocked in tours the same way it is in unit tests.
            this.anchor.value = "25";
            this.anchor.dispatchEvent(new InputEvent("input", { bubbles: true }));
        }
    },
    {
        trigger: ".o_save",
        run: "click",
    },
    // Scan a destination package so the split line function will
    // split the source line into two different lines
    {
        trigger:  ".o_barcode_line.o_selected",
        run: "scan THEPACK2"
    },
    // Assert that the two lines have the source package of the origin line
    {
        trigger: ".o_barcode_line .result-package:contains('THEPACK2')",
        run: () => {
            helper.assertLinesCount(2);
            helper.assertLinePackage(0, "THEPACK1");
            helper.assertLinePackage(1, "THEPACK1");
        }
    },
    { trigger: "button.o_exit", run: "click" },
]});

registry.category("web_tour.tours").add('test_editing_done_picking', { steps: () => [
        { trigger: '.o_barcode_client_action', run: 'scan OBTVALI' },
        {
            trigger: '.o_notification_bar.bg-danger',
            run: function () {
                helper.assertErrorMessage("This picking is already done");
            },
        },
    ]
});

registry.category("web_tour.tours").add("test_split_uncomplete_moves_on_exit", {
    steps: () => [
        {
            trigger: ".o_barcode_line",
            run: "scan product1",
        },
        {
            trigger: ".o_barcode_line[data-barcode='product1'] .qty-done:contains('1')",
        },
        {
            trigger: ".o_edit .fa-pencil",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='qty_done'] input",
        },
        {
            content: "Exit the barcode app to look at look at back end data.",
            trigger: ".o_field_widget[name=product_id] > a",
            run: "click",
        },
        {
            trigger: ".breadcrumb-item.o_back_button",
        },
        {
            content: "Come back to the record in the barcode App.",
            trigger: ".breadcrumb-item.o_back_button",
            run: "click",
        },
        {
            trigger: ".o_barcode_client_action",
        },
        {
            trigger: ".o_barcode_client_action",
            run: () => {
                helper.assertLinesCount(3);
                helper.assertLineQty(0, "0/3");
                helper.assertLineQty(1, "0/5");
                helper.assertLineQty(2, "1/1");
            }
        },
        {
            trigger: ".o_barcode_line",
            run: "scan product2",
        },
        {
            trigger: ".o_barcode_line[data-barcode='product2'] .qty-done:contains('1')",
        },
        {
            trigger: ".o_edit .fa-pencil",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='qty_done'] input",
        },
        {
            content: "Exit the barcode app to look at look at back end data.",
            trigger: ".o_field_widget[name=product_id] > a",
            run: "click",
        },
        {
            trigger: ".breadcrumb-item.o_back_button",
        },
        {
            content: "Come back to the record in the barcode App.",
            trigger: ".breadcrumb-item.o_back_button",
            run: "click",
        },
        {
            trigger: ".o_barcode_client_action",
        },
        {
            trigger: ".o_barcode_client_action",
            run: () => {
                helper.assertLinesCount(4);
                helper.assertLineQty(0, "0/3");
                helper.assertLineQty(1, "0/4");
                helper.assertLineQty(2, "1/1");
                helper.assertLineQty(3, "1/1");
            }
        },
]});

registry.category("web_tour.tours").add('test_split_uncomplete_manually_assigned_moves_on_exit', {
    steps: () => [
        {
            trigger: '.o_barcode_line',
            run: 'scan product1'
        },
        {
            trigger: ".o_barcode_line[data-barcode='product1'] .qty-done:contains('1')",
            run() {},
        },
        // Leave and re-open the picking it directly
        {
            trigger: "button.o_exit",
            run: "click",
        },
        {
            trigger: ".o_stock_barcode_main_menu",
            run: "scan SUMAMOE"
        },
        {
            trigger: ".o_barcode_client_action",
            run: () => {
                helper.assertLinesCount(2);
                helper.assertLineQty(0, "0/2");
                helper.assertLineQty(1, "1/1");
            }
        },
]});

registry.category("web_tour.tours").add("test_sml_sort_order_by_product_category", {  steps: () => [
    {
        trigger: ".o_barcode_client_action",
        run: () => {
            helper.assertLinesCount(3);
            // Product B should be first because it belongs to category A.
            const line1 = document.querySelector('.o_barcode_line:first-child');
            helper.assertLineProduct(line1, "Product B");
            // Product A should comes after Product B because of its category
            // and before Product C because of its product's name.
            const line2 = document.querySelector('.o_barcode_line:nth-child(2)');
            helper.assertLineProduct(line2, "Product A");
            // Product C should be last.
            const line3 = document.querySelector('.o_barcode_line:last-child');
            helper.assertLineProduct(line3, "Product C");
        }
    },
]});

registry.category("web_tour.tours").add('test_barcode_picking_return', { steps: () => [
    {
        trigger: ".o_barcode_client_action",
    },
    {
        trigger: "span.o_scan_message:contains('This picking is already done')",
    },
    // Press return
    {
        trigger: "button.o_create_return",
        run: "click",
    },
    {
        trigger: "span.o_scan_message:contains('Scan a product')",
    },
    {
        trigger: '.o_barcode_line_title > div.o_product_label:contains("product2")',
    },
    // Scan a product not in the original picking
    {
        trigger: "span.o_scan_message:contains('Scan a product')",
        run: "scan product1",
    },
    ...stepUtils.confirmAddingUnreservedProduct(),
    {
        trigger: '.o_barcode_line_title > div.o_product_label:contains("product1")',
    },
    // Press validate before signing the picking
    {
        trigger: "button.o_validate_page",
        run: "click",
    },
]});

registry.category("web_tour.tours").add('test_scan_package_with_decimal', {
    steps: () => [
        {
            content: "Scan package with more than 3.6 kg (275.86 kg)",
            trigger: '.o_barcode_lines',
            run: 'scan P00001',
        },
        {
            trigger: '.o_barcode_line.o_line_completed',
            run: () => {
                helper.assertLinesCount(2);
                helper.assertLineQty(0, "3.6/3.6");
                helper.assertLineQty(1, "272.24");
            }
        },
        ...stepUtils.validateBarcodeOperation(),
    ]
});

registry.category("web_tour.tours").add('test_barcode_signature_flow', { steps: () => [
    {
        trigger: "div.o_kanban_record_title > span:contains(Delivery Orders)",
        run: "click",
    },
    {
        trigger: "button > span:contains(Delivery Order 1)",
        run: "click",
    },
    // Press validate before signing the picking
    {
        trigger: "button.o_validate_page",
        run: "click",
    },
    // Signature modal should be opened. Choose auto signature
    {
        trigger: "a.o_web_sign_auto_button",
        run: "click",
    },
    // Sign the picking
    {
        trigger: ".modal-footer button.btn-primary:enabled",
        run: "click",
    },
    // The picking now should be validated automatically. Wait until the picking is validated
    { trigger: ".o_kanban_tip_filter" },
    {
        trigger: "button > span:contains(Delivery Order 2)",
        run: "click",
    },
    // Open picking settings menu
    {
        trigger: "button.o_barcode_actions",
        run: "click",
    },
    // Press sign button
    {
        trigger: "button.o_sign",
        run: "click",
    },
    // Signature modal should be opened. Choose auto signature
    {
        trigger: "a.o_web_sign_auto_button",
        run: "click",
    },
    // Sign the picking
    {
        trigger: ".modal-footer button.btn-primary:enabled",
        run: "click",
    },
    // Validate the picking
    {
        trigger: "button.o_validate_page",
        run: "click",
    },
    // Wait until the picking is validated
    { trigger: ".o_kanban_tip_filter" },
]});

registry.category("web_tour.tours").add('test_create_backorder_after_qty_modified', { steps: () => [
        { trigger: '.o_edit', run: 'click' },
        { trigger: '.o_digipad_increment', run: 'click' },
        { trigger: '.o_save', run: 'click' },
        { trigger: '.o_validate_page', run: 'click' },
        { trigger: '.modal-dialog button.btn-primary', run: 'click' },
    ]
});

registry.category("web_tour.tours").add('test_open_picking_dont_override_assigned_user', { steps: () => [
    {
        trigger: '.o_button_operations',
        run: 'click',
    },
    {
        trigger: '.o_kanban_record_title > span:contains(Receipts)',
        run: 'click',
    },
    {
        trigger: '.o_facet_value:contains("To Do") + .o_facet_remove',
        run: 'click',
    },
    {
        trigger: '.btn > span:contains("test_responsible_receipt")',
        run: 'click',
    },
    {
        trigger: '.o_exit',
        run: 'click',
    },
    {
        trigger: '.o_breadcrumb > ol > li > a:contains(Operations)',
    },
]});

registry.category("web_tour.tours").add('test_serial_product_packaging', { steps: () => [
    { trigger: ".o_stock_barcode_main_menu", run: "scan WHIN" },
    { trigger: '.o_barcode_client_action', run: "scan PCK4" },
    {
        trigger: '.o_barcode_line.o_highlight',
        run: function() {
            helper.assertLinesCount(1);
            helper.assertScanMessage('scan_serial');
            helper.assertLineProduct(0, "productserial1");
            helper.assertLineQty(0, "0/4");
            helper.assertButtonIsVisible(0, "toggle_sublines", false);
            helper.assertButtonIsVisible(0, "edit");
        }
    },
    { trigger: ".o_barcode_client_action", run: "scan sn1,sn2,sn3,sn4" },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed .o_line_button.o_toggle_sublines',
        run: 'click',
    },
    {
        trigger: '.o_barcode_line.o_selected .o_sublines',
        run: function() {
            const line = helper.getLine();
            helper.assertLineQty(line, "4/4");
            helper.assertSublinesCount(4);
            const sublines = helper.getSublines();
            helper.assertLinesTrackingNumbers(sublines, ["sn4", "sn3", "sn2", "sn1"]);
            helper.assertLineQty(sublines[0], "1");
            helper.assertLineQty(sublines[1], "1");
            helper.assertLineQty(sublines[2], "1");
            helper.assertLineQty(sublines[3], "1");
        }
    },
]});

registry.category("web_tour.tours").add('test_multi_company_record_access_in_barcode', { steps: () => [
        { trigger: '.o_stock_barcode_main_menu', run: 'scan company2_receipt' },
        // Shouldn't have access to company1 prod while in company2 picking type
        { trigger: '.o_barcode_client_action', run: 'scan company1_product' },
        {
            trigger: '.o_notification_bar.bg-danger',
            run: () => {
                helper.assertErrorMessage('This product doesn\'t exist.');
            },
        },
        { trigger: '.o_barcode_client_action', run: 'scan company2_product' },
        { trigger: '.o_barcode_line' },
        { trigger: '.btn.o_validate_page', run: 'click' },
        { trigger: '.o_stock_barcode_main_menu' },
    ]
});

registry.category("web_tour.tours").add('test_no_zero_demand_new_line_from_split', { steps: () => [
        { trigger: '.o_stock_barcode_main_menu', run: 'scan TNZDNLFS picking' },
        { trigger: '.o_edit', run: 'click' },
        { trigger: 'button.o_digipad_increment', run: 'click' },
        { trigger: '.o_save', run: 'click' },
        { trigger: '.o_barcode_line' },
        { trigger: '.o_exit', run: 'click' },
        { trigger: '.o_stock_barcode_main_menu', run: 'scan TNZDNLFS picking' },
        { trigger: '.o_edit', run: 'click' },
        { trigger: 'button.o_digipad_decrement', run: 'click' },
        { trigger: '.o_save', run: 'click' },
        { trigger: '.o_barcode_line' },
        { trigger: '.o_exit', run: 'click' },
        { trigger: '.o_stock_barcode_main_menu'},
    ]
});

registry.category("web_tour.tours").add("test_barcode_pack_lot_tour", {  steps: () => [
    // Pack two units of the same not reserved lot in different packages
    { trigger: '.o_barcode_line', run: "scan LOT005" },
    { trigger: '.o_barcode_line .o_line_lot_name:contains(LOT005)'},
    { trigger: 'button.o_put_in_pack', run: 'click'},
    { trigger: '.o_line_button.o_toggle_sublines', run: 'click'},
    { trigger: '.o_barcode_line:nth-child(2):has(.fa-archive):contains(LOT005)'},
    { trigger: '.o_barcode_line_summary', run: 'click'},
    { trigger: '.o_barcode_line_summary', run: "scan LOT005" },
    { trigger: '.o_barcode_line.o_line_not_completed:contains(LOT005):not(:has(.fa-archive))'},
    { trigger: 'button.o_put_in_pack', run: 'click'},
    // Pack two units of the same reserved lot in different packages
    { trigger: '.o_barcode_line:nth-child(3):has(.fa-archive)'},
    { trigger: '.o_barcode_line_summary', run: "scan LOT004"},
    { trigger: '.o_barcode_line_summary span.qty-done:contains(3)'},
    { trigger: 'button.o_put_in_pack', run: 'click'},
    { trigger: '.o_barcode_line:nth-child(4):has(.fa-archive)'},
    { trigger: '.o_barcode_line_summary', run: 'click'},
    { trigger: '.o_barcode_line_summary', run: "scan LOT004" },
    { trigger: '.o_barcode_line_summary span.qty-done:contains(4)'},
    { trigger: 'button.o_put_in_pack', run: 'click'},
    { trigger: '.o_barcode_line:nth-child(1):has(.fa-archive)'},
    { trigger:  '.btn.o_validate_page', run: 'click'},
    { trigger: '.o_notification_bar.bg-success'},
]});

registry.category("web_tour.tours").add("test_barcode_create_serials_in_batch_with_single_scan", {  steps: () => [
    // Pack two units of the same not reserved lot in different packages
    { trigger: ".o_barcode_line", run: "scan productlot1"},
    { trigger: ".o_barcode_line", run: "scan " + Array.from({ length: 100 }, (_, i) => `SN${(i + 1).toString().padStart(4, "0")}`).join(";")},
    { trigger: ".o_barcode_scanner_qty .qty-done:contains(100)"},
]});

registry.category("web_tour.tours").add("test_barcode_lazy_cache_scan_two_lots", {  steps: () => [
    { trigger: ".o_barcode_line", run: "scan SN-001" },
    { trigger: ".o_barcode_line", run: "scan SN-002" },
    { trigger: ".o_barcode_scanner_qty .qty-done:contains(2)"},
]});

registry.category("web_tour.tours").add('test_scan_location_destination_for_internal_transfers', {
    steps: () => [
        {
            trigger: ".o_button_operations",
            run: "click",
        },
        {
            trigger: ".o_barcode_picking_type:has(.o_kanban_record_title:contains('Internal Transfers'))",
            run: "click",
        },
        {
            trigger: "button.o-kanban-button-new",
        },
        {
            trigger: "button.o-kanban-button-new",
            run: "click",
        },
        {
            trigger: "button.o_add_line:contains('Add Product')",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='product_id'] input.o_input",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='product_id'] input.o_input",
            run: "edit Lovely Product",
        },
        {
            trigger: ".dropdown-item:contains('Lovely Product')",
            run: "click",
        },
        {
            trigger: ".o_save",
            run: "click",
        },
        {
            trigger: ".o_scan_message.o_scan_product_or_dest",
        },
        {
            trigger: ".o_barcode_line",
            run: "scan WH-LOVE",
        },
        {
            trigger: "div[name='destination_location']:contains(Lovely)",
        },
        {
            trigger: '.o_validate_page',
            run: "click",
        },
        {
            trigger: '.o_notification_bar.bg-success',
        },
]});

registry.category("web_tour.tours").add("test_scan_product_when_in_form_view", {
    steps: () => [
        // Scan a location to create an internal picking.
        { trigger: ".o_stock_barcode_main_menu", run: "scan shelf3" },
        // Scan a product and open the form view.
        { trigger: ".o_barcode_client_action", run: "scan product1" },
        { trigger: ".o_barcode_line .o_edit", run: "click" },
        // Update the quantity then scan another product.
        { trigger: ".o_field_widget[name=qty_done] input", run: "edit 5" },
        { trigger: ".o_barcode_line_form", run: "scan product2" },
        {
            trigger: ".o_barcode_line_form",
            run: () => {
                helper.assertFormQuantity("5");
            },
        },
        // Save the change and validate the picking.
        { trigger: ".o_save", run: "click" },
        ...stepUtils.validateBarcodeOperation(".o_barcode_line .qty-done:contains(5)"),
    ],
});

registry.category("web_tour.tours").add("test_fetch_archived_records_in_lazy_barcode_cache", {
    steps: () => [
        {
            trigger: "button.o_add_remaining_quantity",
            run: "click",
        },
        {
            trigger: ".o_validate_page",
            run: "click",
        },
        {
            trigger: ".o_notification_bar.bg-success",
            run() {},
        },
    ]
});

registry.category("web_tour.tours").add("test_validate_uncomplete_return", {
    steps: () => [
        // Open and process the receipt.
        { trigger: ".o_stock_barcode_main_menu", run: "scan TEST/IN/0001" },
        { trigger: ".o_barcode_client_action", run: "scan product1" },
        { trigger: ".o_barcode_line", run: "scan product1" },
        ...stepUtils.validateBarcodeOperation(".o_barcode_line.o_line_completed"),
        // Re-open the receipt and create a return.
        { trigger: ".o_stock_barcode_main_menu", run: "scan TEST/IN/0001" },
        { trigger: "button.o_create_return", run: "click" },
        { trigger: ".o_barcode_line", run: "scan product1" },
        ...stepUtils.validateBarcodeOperation(".o_barcode_line.o_selected"),
        { trigger: ".o_stock_barcode_main_menu" },
        { trigger: ".o_web_client:not(.modal-open)" },
    ],
});

registry.category("web_tour.tours").add("test_select_with_same_product_and_lot", {
    steps: () => [
        {
            trigger: '.o_barcode_client_action',
            run: () => {
                helper.assertLinesCount(1);
                helper.assertValidateVisible(true);
                helper.assertValidateEnabled(true);
            }
        },
        // Unfold grouped lines
        {
            trigger: '.o_line_button.o_toggle_sublines',
            run: 'click',
        },
        {
            trigger: '.o_sublines .o_barcode_line',
            run: () => {
                const sublines = document.querySelectorAll('.o_sublines .o_barcode_line');
                helper.assert(sublines.length, 2, 'it should have 2 sublines');
            }
        },
        // Scan source location
        {
            trigger: '.o_barcode_client_action',
            run: 'scan LOC-01-00-00'
        },
        // Select the second sub-line
        {
            trigger: '.o_sublines .o_barcode_line:last-child',
            run: 'click',
        },
        // Scan the lot 2 times
        {
            trigger: '.o_barcode_client_action',
            run: 'scan lot_xyz',
        },
        {
            trigger: '.o_barcode_scanner_qty .qty-done:contains("1")',
            run() {},
        },
        {
            trigger: '.o_barcode_client_action',
            run: 'scan lot_xyz',
        },
        {
            trigger: '.o_barcode_scanner_qty .qty-done:contains("2")',
            run() {},
        },
        {
            trigger: '.o_barcode_lines',
            run: () => {
                const line1 = document.querySelector('.o_sublines .o_barcode_line:first-child');
                const line2 = document.querySelector('.o_sublines .o_barcode_line:last-child');
                helper.assert(line1.querySelector(
                    '.o_barcode_scanner_qty .qty-done').innerText,
                    '0',
                    'No product should be scanned for the first line'
                );
                helper.assert(
                    line2.querySelector('.o_barcode_scanner_qty .qty-done').innerText,
                    '2',
                    '2 products should be scanned for the second line'
                );
            },
        },
        // Select the first sub-line
        {
            trigger: '.o_sublines .o_barcode_line:first-child',
            run: 'click',
        },
        // Scan the lot 2 times
        {
            trigger: '.o_barcode_client_action',
            run: 'scan lot_xyz',
        },
        {
            trigger: '.o_barcode_scanner_qty .qty-done:contains("3")',
            run() {},
        },
        {
            trigger: '.o_barcode_client_action',
            run: 'scan lot_xyz',
        },
        {
            trigger: '.o_barcode_scanner_qty .qty-done:contains("4")',
            run() {},
        },
        {
            trigger: '.o_barcode_line.o_line_completed',
            run: () => {
                // Main line should be completed
                helper.assertLinesCount(1);
                // Both sub-lines should be completed
                helper.assert(
                    document.querySelectorAll('.o_sublines .o_barcode_line.o_line_completed').length,
                    2,
                    'Both sublines should be completed'
                );
            },
        },
    ]
});

registry.category("web_tour.tours").add("test_description_picking_tour", { steps: () => [
    { trigger: '.o_stock_barcode_main_menu', run: 'scan WHIN' },
    { trigger: '.o_barcode_client_action', run: 'scan test_product' },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add("test_uom_update_picking_tour", { steps: () => [
    // Open the operations menu
    {
        trigger: ".o_button_operations",
        run: "click",
    },
    // Click on the 'Receipts' test_product_uom_partner
    {
        trigger: ".o_kanban_record:contains('Receipts')",
        run: "click",
    },
    // Wait until the 'Operations' breadcrumb is visible
    {
        trigger: ".breadcrumb:contains('Operations')"
    },
    {
        trigger: ".o_kanban_record:contains('test_product_uom_partner')",
        run: "click",
    },
    // Click the pencil to edit the line
    {
        trigger: ".o_barcode_line .o_edit",
        run: "click",
    },
    // Open the UoM dropdown
    {
        trigger: ".o_field_widget[name='product_uom_id'] input",
        run: "click",
    },
    // Select the 'Dozen' UoM
    {
        trigger: ".ui-menu-item > a:contains('Dozen')",
        run: "click",
    },
    {
        trigger: ".o_digipad_increment",
        run: "click",
    },
    // Save the changes
    {
        trigger: ".o_barcode_control .o_save",
        run: "click",
    },
    {
        trigger: ".o_line_uom:contains(/Dozens/)",
    },
    {
        trigger: ".qty-done:text(1)",
    },
    {
        trigger: ".o_barcode_scanner_qty span:eq(1):text(/10)",
    },
]});

registry.category("web_tour.tours").add("test_no_validate_no_dest_package", {
    steps: () => [
    {
        trigger: "button.o_button_operations",
        run: "click",
    },
    {
        trigger: ".o_kanban_record:contains(Internal)",
        run: "click",
    },
    {
        trigger: "button.o-kanban-button-new",
        run: "click",
    },
    {
        trigger: ".o_barcode_client_action",
        run: "scan LOC-01-00-00"
    },
    {
        trigger: ".o_barcode_client_action",
        run: "scan Pack1"
    },
    {
        trigger: ".btn.o_validate_page",
        run: "click",
    },
    {
        trigger: ".o_notification_bar.bg-danger",
        run: () => {
            helper.assertErrorMessage("Destination location must be scanned");
        },
    },
]});

registry.category("web_tour.tours").add("test_remove_sublines_and_scan_serial_again", {
    steps: () => [
        { trigger: ".o_barcode_line:nth-child(1)", run: "click" },
        { trigger: ".o_barcode_line.o_selected", run: "scan abc1" },
        { trigger: ".o_barcode_line.o_selected", run: "scan abc2" },
        { trigger: ".o_barcode_line.o_selected", run: "scan abc3" },
        { trigger: ".o_barcode_line:nth-child(1) .o_toggle_sublines", run: "click" },
        ...stepUtils.decrementLotLineQty("abc1"),
        ...stepUtils.decrementLotLineQty("abc2"),
        ...stepUtils.decrementLotLineQty("abc3"),
        { trigger: ".o_barcode_line:nth-child(1)", run: "click" },
        { trigger: ".o_barcode_line.o_selected", run: "scan abc3" },
        { trigger: ".o_barcode_line.o_selected", run: "scan abc2" },
        { trigger: ".o_barcode_line.o_selected", run: "scan abc1" },
        { trigger: ".o_barcode_line:nth-child(1) .o_barcode_line_details:contains(3/3)"},
        { trigger: ".o_validate_page", run: "click" },
    ],
});

registry.category("web_tour.tours").add("test_scan_package_with_different_uom", {
    steps: () => [
        {
            trigger: '.o_barcode_client_action',
            run: 'scan LOC-01-00-00',
        },
        {
            trigger: '.o_barcode_client_action',
            run: 'scan package001',
        },
        {
            trigger: '.o_barcode_line.o_line_completed',
            run: function() {
                helper.assertLinesCount(1);
            },
        },
        {
            trigger: '.o_barcode_scanner_qty .qty-done:contains("10000")',
            run() {},
        },
    ]
});

registry.category("web_tour.tours").add("test_quantity_distribution_sublines_same_lot", {
    steps: () => [
        {
            trigger: ".o_barcode_client_action",
            run: "scan lot 1",
        },
        {
            trigger: ".o_barcode_client_action",
            run: "scan lot 1",
        },
        ...stepUtils.validateBarcodeOperation(".o_barcode_location_group > .o_barcode_line.o_line_completed"),
    ]
});

registry.category("web_tour.tours").add("test_rental_partial_reception", {
    steps: () => [
        {
            trigger: ".o_barcode_client_action",
            run: "scan RNT01",
        },
        {
            trigger: '.o_barcode_line[data-barcode="RNT01"] .qty-done:contains("1")',
            run: 'scan OBTVALI',
        },
        {
            trigger: ".modal-content.o_barcode_backorder_dialog",
            run: function() {
                const incompleteLines = document.querySelectorAll(".o_barcode_backorder_product_row");
                helper.assert(incompleteLines.length, 1);
                const line = incompleteLines[0];
                helper.assert(line.querySelector("[name='qty-done']").innerText, "1");
                helper.assert(line.querySelector("[name='reserved-qty']").innerText, "4");
                helper.assert(line.querySelector("[name='backorder-qty']").innerText, "3");
            },
        },
        {
            trigger: ".modal-dialog button.btn-primary",
            run: "click",
        },
        {
            trigger: ".o_notification",
            run: function() {
                const backorderLink = document.querySelector(".o_notification_buttons span");
                helper.assert(
                    backorderLink.innerText.includes("WH/IN/"), true,
                    "The notification should contain a link to the created backorder."
                );
            },
        },
    ]
});

registry.category("web_tour.tours").add("test_no_validate_multiple_times", {
    steps: () => [
        {
            trigger: "button.o_button_operations",
            run: "click",
        },
        {
            trigger: ".o_kanban_record:contains(Internal)",
            run: "click",
        },
        {
            trigger: "button.o-kanban-button-new",
            run: "click",
        },
        {
            trigger: ".o_barcode_client_action",
            run: "scan product2"
        },
        {
            trigger: ".o_barcode_client_action",
            run: "scan LOC-01-01-00"
        },
        {
            trigger: ".btn.o_validate_page.btn-primary",
        },
        {
            trigger: ".o_barcode_client_action",
            async run(helpers) {
                for (let i = 0; i < 2; i++) {
                    helpers.scan('O-BTN.validate');
                }
            }
        },
        {
            trigger: '.o_notification_bar.bg-success',
        },
    ]
});

registry.category("web_tour.tours").add("test_gs1_receipt_multiple_extra_items", {
    steps: () => [
        {
            trigger: ".o_barcode_client_action",
            run: "scan 0112345678900005", // Wanted product
        },
        {
            trigger: ".o_barcode_line[data-barcode='12345678900005'] .qty-done:contains('1')",
            run: "scan 0112345678900012", // Extra product 1
        },
        {
            trigger: ".modal-content .o_barcode_extra_product_dialog div.row[data-barcode='12345678900012'] span.col-3:contains('1')",
            run: "scan 01123456789000123010", // Extra product 1 (10 qty)
        },
        {
            trigger: ".modal-content .o_barcode_extra_product_dialog div.row[data-barcode='12345678900012'] span.col-3:contains('11')",
            run: "scan 011234567890002921001", // Extra product 2 (Serial 001)
        },
        {
            trigger: ".modal-content .o_barcode_extra_product_dialog div.row[data-barcode='12345678900029'] span.col-3:contains('1')",
            run: "scan 011234567890002921002", // Extra product 2 (Serial 002)
        },
        {
            trigger: ".modal-content .o_barcode_extra_product_dialog div.row[data-barcode='12345678900029'] span.col-3:contains('2')",
            run: "scan 011234567890003610L001#305", // Extra product 3 (Lot L001, Qty 5)
        },
        {
            trigger: ".modal-content .o_barcode_extra_product_dialog div.row[data-barcode='12345678900036'] span.col-3:contains('5')",
            run: "scan 011234567890003610L001#305", // Extra product 3 (Lot L001, Qty 5) scanned again, should increase the quantity but not the number of lines
        },
        {
            trigger: ".modal-content .o_barcode_extra_product_dialog div.row[data-barcode='12345678900036'] span.col-3:contains('10')",
            run: "scan 011234567890002921002", // Serial already in list & awaiting confirmation -> Skipped, notification should be shown
        },
        {
            trigger: ".o_notification_bar.bg-danger",
            run: function() {
                helper.assertErrorMessage("The scanned serial number 002 is already awaiting confirmation.");
            },
        },
        {
            trigger: ".modal-content .o_barcode_extra_product_dialog div.row[data-barcode='12345678900012'] input[type='checkbox']",
            run: "uncheck", //Remove Extra Product 1 from selected products
        },
        {
            trigger: ".modal-dialog button.btn-primary",
            run: "click",
        },
        {
            trigger: "button.o_toggle_sublines",
            run: "click", // Open the sublines of the serial product to see all the tracked items
        },
        {
            trigger: ".o_barcode_client_action",
            run: function() {
                helper.assertLinesCount(3);
                helper.assertSublinesCount(2);
                helper.assertLineQty(0, "1/2 Units");
                helper.assertLineQty(1, "2 Units");
                helper.assertLineTrackingNumber(2, "001");
                helper.assertLineTrackingNumber(3, "002");
                helper.assertLineQty(4, "10 Units");
                helper.assertLineTrackingNumber(4, "L001");
            },
        },
    ]
});

registry.category("web_tour.tours").add("test_quantity_updates_on_exit_spam", {
    steps: () => [
        {
            trigger: ".o_stock_barcode_main_menu",
            run: "scan Lovely Delivery"
        },
        {
            trigger: ".o_barcode_client_action",
            run: "scan product1",
        },
        {
            trigger: ".o_barcode_line.o_selected",
            run: () => {
                helper.assertLinesCount(1);
                helper.assertLineQty(0, "1");
            },
        },
        {
            trigger: "button.o_exit",
            run: () => {
                const exitBtn = document.querySelector("button.o_exit");
                exitBtn.click();
                exitBtn.click();
                exitBtn.click();
            },
        },
        {
            trigger: ".o_stock_barcode_main_menu",
        },
    ]
});
