/** @odoo-module */

import helper from '@stock_barcode/../tests/tours/tour_helper_stock_barcode';
import { registry } from "@web/core/registry";
import { stepUtils } from "./tour_step_utils";

registry.category("web_tour.tours").add('test_internal_picking_from_scratch', {test: true, steps: () => [
    /* Move 2 product1 from WH/Stock/Section 1 to WH/Stock/Section 2.
     */
    {
        trigger: '.o_add_line',
    },

    {
        extra_trigger: '.o_field_widget[name="product_id"]',
        trigger: ".o_field_widget[name=qty_done] input",
        run: 'text 2',
    },

    {
        trigger: ".o_field_widget[name=product_id] input",
        run: 'text product1',
    },

    {
        trigger: ".ui-menu-item > a:contains('product1')",
    },

    {
        trigger: ".o_field_widget[name=location_id] input",
        run: 'text Section 1',
    },

    {
        trigger: ".ui-menu-item > a:contains('Section 1')",
    },

    {
        trigger: ".o_field_widget[name=location_dest_id] input",
        run: 'text Section 2',
    },

    {
        trigger: ".ui-menu-item > a:contains('Section 2')",
    },

    {
        trigger: '.o_save',
    },

    {
        trigger: '.o_barcode_line .o_line_source_location:contains("Section 1")',
        extra_trigger: '.o_barcode_line .o_line_destination_location:contains("Section 2")',
        run: function() {
            helper.assertLinesCount(1);
        },
    },

    /* Move 1 product2 from WH/Stock/Section 1 to WH/Stock/Section 3.
     */
    {
        trigger: '.o_add_line',
    },

    {
        extra_trigger: '.o_field_widget[name="product_id"]',
        trigger: ".o_field_widget[name=product_id] input",
        run: 'text product2',
    },

    {
        trigger: ".ui-menu-item > a:contains('product2')",
    },

    {
        trigger: ".o_field_widget[name=location_id] input",
        run: 'text Section 1',
    },

    {
        trigger: ".ui-menu-item > a:contains('Section 1')",
    },

    {
        trigger: ".o_field_widget[name=location_dest_id] input",
        run: 'text WH/Stock/Section 3',
    },

    {
        trigger: ".ui-menu-item > a:contains('Section 3')",
    },

    {
        trigger: '.o_save',
    },

    {
        trigger: '.o_barcode_line .o_line_source_location:contains("Section 1")',
        extra_trigger: '.o_barcode_line .o_line_destination_location:contains("Section 3")',
        run: function() {
            helper.assertLinesCount(2);
            const lineProduct1 = helper.getLine({barcode: 'product1'});
            helper.assertLineIsHighlighted(lineProduct1, false);
            const lineProduct2 = helper.getLine({barcode: 'product2'});
            helper.assertLineIsHighlighted(lineProduct2, true);
        },
    },

    // Edits the first line to check the transaction doesn't crash and the form view is correctly filled.
    { trigger: '.o_barcode_line:first-child .o_edit' },
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
    },

    /* Move 1 product2 from WH/Stock/Section 1 to WH/Stock/Section 2.
     */
    {
        trigger: '.o_add_line',
    },

    {
        extra_trigger: '.o_field_widget[name="product_id"]',
        trigger: ".o_field_widget[name=product_id] input",
        run: 'text product2',
    },

    {
        trigger: ".ui-menu-item > a:contains('product2')",
    },

    {
        trigger: ".o_field_widget[name=location_id] input",
        run: 'text Section 1',
    },

    {
        trigger: ".ui-menu-item > a:contains('Section 1')",
    },

    {
        trigger: ".o_field_widget[name=location_dest_id] input",
        run: 'text Section 2',
    },

    {
        trigger: ".ui-menu-item > a:contains('Section 2')",
    },

    {
        trigger: '.o_save',
    },

    {
        trigger: '.o_barcode_line.o_selected .o_line_source_location:contains("Section 1")',
        extra_trigger: '.o_barcode_line.o_selected .o_line_destination_location:contains("Section 2")',
        run: function() {
            helper.assertLinesCount(3);
        },
    },
    // Scans the destination (Section 2) for the current line...
    { trigger: '.o_barcode_line:nth-child(2).o_selected', run: 'scan LOC-01-02-00' },
    // ...then scans the source (Section 1) for the next line.
    { trigger: '.o_barcode_client_action', run: 'scan LOC-01-01-00' },
    // On this page, scans product1 which will create a new line and then opens its edit form view.

    {
        trigger: '.o_line_source_location .fw-bold:contains("Section 1")',
        run: 'scan product1'
    },

    { // First call to write.
        trigger: '.o_barcode_line[data-barcode="product1"].o_selected .o_edit',
    },

    {
        trigger :'.o_save',
        extra_trigger: '.o_field_widget[name="product_id"]:contains("product1")',
    },
    { // Scans the line's destination before to validate the picking.
        trigger: '.o_barcode_line[data-barcode="product1"].o_selected',
        run: 'scan shelf3',
    },

    {
        extra_trigger: '.o_barcode_line:last-child() .o_line_destination_location:contains("Section 3")',
        trigger: '.o_validate_page',
    },
    { // Second call to write (change the dest. location).
        trigger: '.o_notification.border-success',
        isCheck: true,
    }
]});

registry.category("web_tour.tours").add('test_internal_picking_from_scratch_with_package', { test: true, steps: () => [
    // Creates a first internal transfert (Section 1 -> Section 2).
    { trigger: '.o_stock_barcode_main_menu', run: 'scan WH-INTERNAL' },
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
        run: 'scan O-BTN.validate',
    },
    { trigger: '.o_notification.border-success' },
    { trigger: '.o_notification button.o_notification_close' },

    // Creates a second internal transfert (WH/Stock -> WH/Stock).
    { trigger: '.o_stock_barcode_main_menu', run: 'scan WH-INTERNAL' },
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
    { trigger: '.o_barcode_line:not(.o_selected)', run: 'scan O-BTN.validate' },
    { trigger: '.o_notification.border-success', isCheck: true },
]});

registry.category("web_tour.tours").add('test_internal_picking_reserved_1', {test: true, steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(3);
            helper.assertScanMessage('scan_src');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
            helper.assertLineIsHighlighted(0, false);
            helper.assertLineLocations(0, '.../Section 1', '.../Section 2');
            helper.assertLineIsHighlighted(1, false);
            helper.assertLineLocations(1, '.../Section 1', '.../Section 2');
            helper.assertLineIsHighlighted(2, false);
            helper.assertLineLocations(2, '.../Section 3', '.../Section 4');
        }
    },

    /* We first move a product1 from shef3 to shelf2.
     */
    {
        trigger: '.o_barcode_client_action',
        run: 'scan shelf3'
    },

    {
        trigger: '.o_barcode_line .o_line_source_location .fw-bold:contains("Section 3")',
        run: function() {
            helper.assertLinesCount(3);
            helper.assertScanMessage('scan_product');
            const locationInBold = document.querySelector('.o_line_source_location .fw-bold');
            const lineInSection3 = locationInBold.closest('.o_barcode_line');
            helper.assertLineLocations(lineInSection3, '.../Section 3', '.../Section 4');
        }
    },

    { // Scanning product1 after scanned shelf3 will select the existing line but change its source.
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },

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
            helper.assertLineLocations(lineproduct1, '.../Section 3', '.../Section 2');
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-02-00'
    },

    {
        trigger: '.o_barcode_line:not(.o_selected):first-child .o_line_destination_location:contains(".../Section 2")',
        run: function() {
            helper.assertLinesCount(3);
            helper.assertScanMessage('scan_src');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
            const lineproduct1 = helper.getLine({barcode: 'product1'});
            helper.assertLineIsHighlighted(lineproduct1, false);
            helper.assertLineLocations(lineproduct1, '.../Section 3', '.../Section 2');
        }
    },

    // Scans Section 1 as source location.
    { 'trigger': '.o_barcode_client_action', run: 'scan LOC-01-01-00' },

    {
        trigger: '.o_line_source_location .fw-bold:contains("Section 1")',
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
        trigger: '.o_barcode_line:nth-child(4).o_selected',
        run: function() {
            helper.assertLinesCount(4);
            helper.assertScanMessage('scan_product_or_dest');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
            helper.assertLineIsHighlighted(0, false);
            helper.assertLineIsHighlighted(1, false);
            helper.assertLineIsHighlighted(2, false);
            helper.assertLineIsHighlighted(3, true);
            helper.assertLineLocations(3, '.../Section 1', 'WH/Stock');
        }
    },
    { trigger: '.o_barcode_client_action', run: 'scan LOC-01-02-00' },

    // Process the reservation for product2 (Section 1 to Section 2).
    { trigger: '.o_scan_message.o_scan_src', run: 'scan LOC-01-01-00' },
    { trigger: '.o_scan_message.o_scan_product', run: 'scan product2' },
    {
        trigger: '.o_barcode_line:nth-child(2).o_selected',
        run: function() {
            helper.assertLinesCount(4);
            helper.assertScanMessage('scan_dest');
            helper.assertValidateIsHighlighted(false);
            helper.assertLineIsHighlighted(0, false);
            helper.assertLineIsHighlighted(1, true);
            helper.assertLineIsHighlighted(2, false);
            helper.assertLineIsHighlighted(3, false);
        }
    },
    { trigger: '.o_barcode_client_action', run: 'scan LOC-01-02-00' },

    // Process the reservation for product2 (Section 3 to Section 4).
    { trigger: '.o_scan_message.o_scan_src', run: 'scan shelf3' },
    { trigger: '.o_scan_message.o_scan_product', run: 'scan product2' },
    {
        trigger: '.o_barcode_line:nth-child(3).o_selected',
        run: function() {
            helper.assertLinesCount(4);
            helper.assertScanMessage('scan_dest');
            helper.assertValidateIsHighlighted(false);
            helper.assertLineIsHighlighted(0, false);
            helper.assertLineIsHighlighted(1, false);
            helper.assertLineIsHighlighted(2, true);
            helper.assertLineIsHighlighted(3, false);
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
            helper.assertLineQty(0, '1 / 1');
            helper.assertLineLocations(0, '.../Section 3', '.../Section 2');

            helper.assertLineIsHighlighted(1, false);
            helper.assertLineQty(1, '1 / 1');
            helper.assertLineLocations(1, '.../Section 1', '.../Section 2');

            helper.assertLineIsHighlighted(2, false);
            helper.assertLineQty(2, '1 / 1');
            helper.assertLineLocations(2, '.../Section 3', '.../Section 4');

            helper.assertLineIsHighlighted(3, false);
            helper.assertLineQty(3, '1');
            helper.assertLineLocations(3, '.../Section 1', '.../Section 2');
        }
    },
]});

registry.category("web_tour.tours").add('test_procurement_backorder', {
    test: true, steps: () => [
        { trigger: '.o_barcode_client_action', run: 'scan PB' },
        { trigger: '.o_barcode_line:contains("PB")', run: 'scan O-BTN.validate' },
        { trigger: '.o_notification.border-success', isCheck: true },
    ]
});

registry.category("web_tour.tours").add('test_receipt_reserved_1', {test: true, steps: () => [
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
    { trigger: '.o_barcode_line.o_selected.o_line_completed', run: 'scan WH-STOCK-2' },
    {
        trigger: '.o_notification.border-danger',
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

    // Open manual scanner.
    {
        trigger: '.o_barcode_client_action .o_stock_mobile_barcode',
    },

    // Manually add 'product1'.
    {
        trigger: '.modal-content .modal-body #manual_barcode',
        run: function(actions) {
            var barcode = 'product1';
            actions.text(barcode);
        }
    },

    // Apply the manual entry of barcode.
    {
        trigger: '.modal-content .modal-footer .btn-primary:not(:disabled)',
    },

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
    },
    {
        trigger: '.o_field_widget[name="product_id"]',
        run: function() {
            helper.assertFormLocationDest('WH/Stock');
        },
    },
    ...stepUtils.discardBarcodeForm(),
]});

registry.category("web_tour.tours").add('test_receipt_reserved_2_partial_put_in_pack', {test: true, steps: () => [
    // Scan the picking's name to open it.
    { trigger: '.o_stock_barcode_main_menu', run: 'scan receipt_test' },
    {
        trigger: '.o_barcode_line',
        run: function() {
            helper.assertLinesCount(2);
            helper.assertLineProduct(0, "product1");
            helper.assertLineQty(0, "0 / 3");
            helper.assertLineProduct(1, "product2");
            helper.assertLineQty(1, "0 / 3");
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
            helper.assertLineQty(0, "2 / 3");
            helper.assertLineProduct(1, "product2");
            helper.assertLineQty(1, "0 / 3");
        },
    },
    { trigger: '.o_barcode_client_action', run: 'scan O-BTN.pack'},
    {
        trigger: '.o_barcode_line:contains("PACK0001000")',
        run: function() {
            const lines = helper.getLines();
            helper.assert(lines.length, 3);

            helper.assertLineProduct(lines[0], "product1");
            helper.assertLineQty(lines[0], "0 / 1");
            helper.assert(lines[0].querySelector('.result-package'), null);

            helper.assertLineProduct(lines[1], "product2");
            helper.assertLineQty(lines[1], "0 / 3");
            helper.assert(lines[1].querySelector('.result-package'), null);

            helper.assertLineProduct(lines[2], "product1");
            helper.assertLineQty(lines[2], "2 / 2");
            helper.assert(lines[2].querySelector('.result-package').innerText, "PACK0001000");
        },
    },

    // Scan product1 and product2 then put in pack.
    { trigger: '.o_barcode_client_action', run: 'scan product1'},
    { trigger: '.o_barcode_line.o_selected.o_line_completed', run: 'scan product2'},
    {
        trigger: '.o_barcode_line.o_selected .qty-done:contains("1")',
        run: function() {
            const lines = helper.getLines();
            helper.assert(lines.length, 3);

            helper.assertLineProduct(lines[0], "product1");
            helper.assertLineQty(lines[0], "1 / 1");
            helper.assert(lines[0].querySelector('.result-package'), null);

            helper.assertLineProduct(lines[1], "product2");
            helper.assertLineQty(lines[1], "1 / 3");
            helper.assert(lines[1].querySelector('.result-package'), null);

            helper.assertLineProduct(lines[2], "product1");
            helper.assertLineQty(lines[2], "2 / 2");
            helper.assert(lines[2].querySelector('.result-package').innerText, "PACK0001000");
        },
    },
    { trigger: '.o_put_in_pack' },
    {
        trigger: '.o_barcode_line:contains("PACK0001001")',
        run: function() {
            const lines = helper.getLines();
            helper.assert(lines.length, 4);

            helper.assertLineProduct(lines[0], "product2");
            helper.assertLineQty(lines[0], "0 / 2");
            helper.assert(lines[0].querySelector('.result-package'), null);

            helper.assertLineProduct(lines[1], "product1");
            helper.assertLineQty(lines[1], "2 / 2");
            helper.assert(lines[1].querySelector('.result-package').innerText, "PACK0001000");

            helper.assertLineProduct(lines[2], "product1");
            helper.assertLineQty(lines[2], "1 / 1");
            helper.assert(lines[2].querySelector('.result-package').innerText, "PACK0001001");

            helper.assertLineProduct(lines[3], "product2");
            helper.assertLineQty(lines[3], "1 / 1");
            helper.assert(lines[3].querySelector('.result-package').innerText, "PACK0001001");
        },
    },
    // Confirm the backorder, then close the receipt.
    { trigger: '.btn.o_validate_page' },
    { trigger: '.modal-dialog button.btn-primary' },
    { trigger: '.o_notification.border-success', isCheck: true },
]});

registry.category("web_tour.tours").add('test_receipt_product_not_consecutively', {test: true, steps: () => [
    // Scan two products (product1 - product2 - product1)
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    { trigger: '.o_barcode_line', run: 'scan product2' },
    { trigger: '.o_barcode_line:contains("product2")', run: 'scan product1' },
    {
        trigger: '.o_barcode_line[data-barcode="product1"] .qty-done:contains("2")',
        run: 'scan O-BTN.validate',
    },
    {
        trigger: '.o_notification.border-success',
        isCheck: true,
    },
]});

registry.category("web_tour.tours").add("test_delivery_source_location", {test: true, steps: () => [
    // FIRST DELIVERY (using stock from WH/Stock)
    { trigger: ".o_stock_barcode_main_menu", run: 'scan delivery_from_stock' },
    // Tries to scan a location who doesn't belong to the delivery's source location.
    { trigger: '.o_scan_message.o_scan_src', run: 'scan WH-SECOND-STOCK' },
    {
        trigger: '.o_notification.border-danger',
        run: () => {
            helper.assertErrorMessage("The scanned location doesn't belong to this operation's location");
    }},
    { trigger: 'button.o_notification_close' },
    // Scans the right location now.
    { trigger: '.o_barcode_client_action', run: 'scan LOC-01-00-00' },
    { trigger: '.o_scan_message.o_scan_product', run: 'scan product1' },
    { trigger: '.o_barcode_line.o_selected', run: 'scan product1' },
    { trigger: '.o_barcode_line.o_selected', run: 'scan product1' },
    { trigger: '.o_barcode_line.o_selected', run: 'scan product1' },
    { trigger: '.o_validate_page.btn-success' },

    // SECOND DELIVERY (using stock from WH/Second Stock)
    { trigger: ".o_stock_barcode_main_menu", run: 'scan delivery_from_second_stock' },
    // Tries to scan a location who doesn't belong to the delivery's source location.
    { trigger: '.o_scan_message.o_scan_src', run: 'scan LOC-01-00-00' },
    {
        trigger: '.o_notification.border-danger',
        run: () => {
            helper.assertErrorMessage("The scanned location doesn't belong to this operation's location");
    }},
    { trigger: 'button.o_notification_close' },
    // Scans the right location now.
    { trigger: '.o_barcode_client_action', run: 'scan WH-SECOND-STOCK' },
    { trigger: '.o_scan_message.o_scan_product', run: 'scan product1' },
    { trigger: '.o_barcode_line.o_selected', run: 'scan product1' },
    { trigger: '.o_barcode_line.o_selected', run: 'scan product1' },
    { trigger: '.o_barcode_line.o_selected', run: 'scan product1' },
    ...stepUtils.validateBarcodeOperation('.o_validate_page.btn-success'),

    // Create a delivery on the fly and try to use both locations as source.
    // Since the delivery is not planned and there is no way for the user to set
    // that from the Barcode app, it should be possible.
    { trigger: ".o_stock_barcode_main_menu", run: 'scan WH-DELIVERY' },
    { trigger: '.o_barcode_client_action', run: 'scan WH-SECOND-STOCK' },
    { trigger: '.o_scan_message.o_scan_product', run: 'scan product1' },
    { trigger: '.o_barcode_line', run: 'scan LOC-01-00-00' },
    { trigger: '.o_scan_message.o_scan_validate', run: 'scan product1' },
    {
        trigger: '.o_barcode_line+.o_barcode_line',
        run: () => {
            helper.assertLinesCount(2);
            helper.assertLineSourceLocation(0, "WH/Second Stock");
            helper.assertLineSourceLocation(1, "WH/Stock");
        }
    },
]});

registry.category("web_tour.tours").add("test_delivery_lot_with_multi_companies", {test: true, steps: () => [
    // Scans tsn-002: should find nothing since this SN belongs to another company.
    { trigger: ".o_barcode_client_action", run: "scan tsn-002" },
    // Checks a warning was displayed and scans tsn-001: a line should be added.
    { trigger: ".o_notification.border-danger", run: "scan tsn-001" },
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
        extra_trigger: ".o_toggle_sublines", // Should have sublines since there is two SN.
        trigger: ".o_validate_page",
    },
    { trigger: ".o_notification.border-success", isCheck: true },
]});

registry.category("web_tour.tours").add('test_delivery_lot_with_package', {test: true, steps: () => [
    // Unfold grouped lines.
    { trigger: '.o_line_button.o_toggle_sublines' },
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
    },
    {
        trigger: '.o_field_widget[name="product_id"]',
        run: function() {
            helper.assertFormQuantity("1");
            helper.assert($('div[name="package_id"] input').val(), "pack_sn_2");
            helper.assert($('div[name="result_package_id"] input').val(), "");
            helper.assert($('div[name="owner_id"] input').val(), "Particulier");
            helper.assert($('div[name="lot_id"] input').val(), "sn4");
        },
    },
    {
        trigger: '.o_discard',
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_delivery_lot_with_package_delivery_step', {test: true, steps: () => [
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
        run: 'scan O-BTN.validate'
    },
    {
        trigger: '.o_notification.border-success',
        run: function () {
            helper.assertErrorMessage('The transfer has been validated');
        },
    },
]});

registry.category("web_tour.tours").add('test_delivery_reserved_1', {test: true, steps: () => [
    // test that picking note properly pops up + close it
    { trigger: '.alert:contains("A Test Note")' },
    { trigger: '.alert button.btn-close' },
    // Opens and close the line's form view to be sure the note is still hidden.
    { trigger: '.o_add_line' },
    { trigger: '.o_discard' },
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
        trigger: '.o_barcode_client_action',
        run: 'scan product2'
    },

    // Display the picking's information to trigger a save.
    { trigger: '.o_show_information' },
    { trigger: '.o_barcode_control .btn.o_discard' },
    {
        trigger: '.o_barcode_line',
        isCheck: true,
    },
]});

registry.category("web_tour.tours").add('test_delivery_reserved_2', {test: true, steps: () => [
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
    stepUtils.confirmAddingUnreservedProduct(),

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
            [0, 1].map(i => helper.assertLineQty(lines[i], "2 / 2"));
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

registry.category("web_tour.tours").add('test_delivery_reserved_3', {test: true, steps: () => [
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
            helper.assertLineQty(0, "1 / 1");
        }
    },
]});

registry.category("web_tour.tours").add("test_delivery_reserved_4_backorder", { test: true, steps: () => [
    {
        trigger: ".o_barcode_client_action",
        run: function() {
            // The picking has 3 moves but only 2 barcode lines because the move for product3
            // has no reservation, so no move line, so no barcode line neither.
            helper.assertLinesCount(2);
            helper.assertLineQty(0, "0 / 4"); // 4 demand, 4 reserved.
            helper.assertLineQty(1, "0 / 2"); // 4 demand but only 2 reserved.
        }
    },
    // Scans product1 then tries to validate again -> Should display the backorder dialog.
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    {
        extra_trigger: ".o_barcode_line.o_selected",
        trigger: ".o_validate_page",
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
    { trigger: ".modal-dialog button.btn-secondary" }, // Cancel -> Stay on the delivery.
    // Scans 3 more times product1 to complete the line then clicks on validate again.
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    {
        extra_trigger: ".o_barcode_line.o_selected.o_line_completed",
        trigger: ".o_validate_page",
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
    { trigger: ".modal-dialog button.btn-primary" }, // Validate -> Should create a backorder.
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

registry.category("web_tour.tours").add('test_delivery_using_buttons', {test: true, steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(3);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
            helper.assert(
                $('.o_line_button[name=incrementButton]').length, 3,
                "3 buttons must be present in the view (one by line)"
            );
            helper.assertLineQty(0, "0 / 2");
            helper.assertLineQty(1, "0 / 3");
            helper.assertLineQty(2, "0 / 4");
            helper.assertButtonShouldBeVisible(0, "add_quantity");
            helper.assertButtonShouldBeVisible(1, "add_quantity");
            helper.assertButtonShouldBeVisible(2, "add_quantity");
        }
    },

    // On the first line, goes on the form view and press digipad +1 button.
    { trigger: '.o_barcode_line:first-child .o_edit' },
    { trigger: '.o_digipad_button.o_increase' },
    { trigger: '.o_save' },
    {
        trigger: '.o_barcode_lines',
        run: function() {
            helper.assertButtonShouldBeVisible(0, "add_quantity");
            helper.assertLineQty(0, '1 / 2');
            helper.assertLineIsHighlighted(0, true);
            helper.assertLineIsHighlighted(1, false);
            helper.assertLineIsHighlighted(2, false);
        }
    },
    // Press +1 button again, now its buttons must be hidden.
    {
        trigger: '.o_barcode_line:first-child .o_add_quantity'
    },
    {
        trigger: '.o_barcode_line:first-child.o_selected.o_line_completed',
        run: function() {
            helper.assertButtonShouldBeVisible(0, "add_quantity", false);
            helper.assertLineQty(0, '2 / 2');
            helper.assertButtonShouldBeVisible(1, "add_quantity");
            helper.assertLineQty(1, '0 / 3');
        }
    },
    // Press the add remaining quantity button.
    { trigger: '.o_barcode_line:nth-child(2) .o_add_quantity' },
    // Product2 is now done, its button must be hidden.
    {
        trigger: '.o_barcode_line:nth-child(2).o_selected.o_line_completed',
        run: function() {
            helper.assertLineButtonsAreVisible(1, false, '[name=incrementButton]');
            helper.assertLineQty(1, '3 / 3');
            helper.assertLineIsHighlighted(0, false);
            helper.assertLineIsHighlighted(1, true);
            helper.assertLineIsHighlighted(2, false);
        }
    },

    // Last line at beginning (product3) now at top of list
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertButtonShouldBeVisible(2, 'add_quantity');
            helper.assertLineQty(2, '0 / 4');
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
            helper.assertButtonShouldBeVisible(2, 'add_quantity');
            helper.assertLineQty(2, '1 / 4');
            helper.assertLineIsHighlighted(0, false);
            helper.assertLineIsHighlighted(1, false);
            helper.assertLineIsHighlighted(2, true);
        }
    },
    // Goes on the form view and press digipad +1 button.
    { trigger: '.o_barcode_line:last-child .o_edit' },
    { trigger: '.o_digipad_button.o_increase' },
    { trigger: '.o_save' },
    {
        trigger: '.o_barcode_lines',
        run: function() {
            helper.assertButtonShouldBeVisible(0, 'add_quantity');
            helper.assertLineQty(0, '2 / 4');
        }
    },
    // Press the add remaining quantity button, then the button must be hidden.
    { trigger: '.o_barcode_line:first-child .o_add_quantity' },
    {
        trigger: '.o_barcode_line:first-child .qty-done:contains("4")',
        run: function() {
            helper.assertLineButtonsAreVisible(0, false, '[name=incrementButton]');
            helper.assertLineQty(0, '4 / 4');
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
            helper.assertLineQty(1, '1');
            // +1 button must be present on new line.
            helper.assertButtonShouldBeVisible(1, 'add_quantity');
        }
    },
    // Press +1 button of the new line.
    {
        trigger: '.o_barcode_line:nth-child(2) .o_add_quantity'
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
            helper.assertButtonShouldBeVisible(1, 'add_quantity');
        }
    },

    // Validate the delivery.
    {
        trigger: '.o_validate_page'
    },
    {
        trigger: '.o_notification.border-success',
        isCheck: true,
    },
]});

registry.category("web_tour.tours").add('test_remaining_decimal_accuracy', {test: true, steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
            helper.assertLineQty(0, "0 / 4");
            helper.assertButtonShouldBeVisible(0, "add_quantity");
        }
    },

    // Goes on the form view and add 2.2 .
    { trigger: '.o_barcode_line:first-child .o_edit' },
    {
        trigger: 'div[name=qty_done] input',
        run: 'text 2.2',
    },
    { trigger: '.o_save' },
    {
        trigger: '.o_barcode_lines',
        run: function() {
            helper.assertButtonShouldBeVisible(0, "add_quantity");
            helper.assertLineQty(0, '2.2 / 4');
            const buttonAddQty = document.querySelector(".o_add_quantity");
            helper.assert(buttonAddQty.innerText, "+1.8", "Something wrong with the quantities");
        }
    },

    // check button is correctly set for digits < 1
    { trigger: '.o_barcode_line:first-child .o_edit' },
    {
        trigger: 'input.o_input[id=qty_done_1]',
        run: 'text 3.5',
    },
    { trigger: '.o_save' },
    {
        trigger: '.o_barcode_lines',
        run: function() {
            helper.assertButtonShouldBeVisible(0, "add_quantity");
            helper.assertLineQty(0, '3.5 / 4');
            const buttonAddQty = document.querySelector(".o_add_quantity");
            helper.assert(buttonAddQty.innerText, "+0.5", "Something wrong with the quantities");
        }
    },
]});

registry.category("web_tour.tours").add('test_receipt_from_scratch_with_lots_1', {test: true, steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.o_notification.border-danger'
    },

    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertErrorMessage('You are expected to scan one or more products.');
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
    { trigger: '.o_barcode_line.o_selected .btn.o_toggle_sublines .fa-caret-down' },

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
    { trigger: '.o_scan_message.o_scan_product_or_dest', run: 'scan WH-STOCK-2' },
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

registry.category("web_tour.tours").add('test_receipt_from_scratch_with_lots_2', {test: true, steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan productlot1'
    },

    { trigger: '.o_barcode_line .o_edit' },

    {
        trigger: '.o_input[id=lot_id_0]',
        run: function () {
            const $lot_name = $('#lot_name_0');
            // Check if the lot_name is invisible
            helper.assert($lot_name.length, 0);
        }
    },

    { trigger: '.o_save' },

    {
        trigger: '.o_barcode_line',
        run: 'scan lot1',
    },

    { trigger: '.o_line_lot_name:contains(lot1)' },

    { trigger: '.o_barcode_line .o_edit' },

    {
        trigger: '.o_input[id="lot_name_0"]',
        run: function () {
            const $lot_id = $('#lot_id_0');
            // check that the lot_id is invisible
            helper.assert($lot_id.length, 0);
         }
    },

    { trigger: '.o_save' },

    {
        trigger: '.o_line_lot_name:contains(lot1)',
        run: 'scan lot1',
    },

    {
        trigger: '.qty-done:contains(2)',
        run: 'scan lot2',
    },
    { trigger: '.o_barcode_line.o_selected .btn.o_toggle_sublines .fa-caret-down' },

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

registry.category("web_tour.tours").add('test_receipt_from_scratch_with_lots_3', {test: true, steps: () => [
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
    { trigger: '.o_barcode_line.o_selected .btn.o_edit' },
    { trigger: '.o_discard' },
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

registry.category("web_tour.tours").add('test_receipt_from_scratch_with_lots_4', {test: true, steps: () => [
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
        trigger: '.o_add_line',
        extra_trigger: '.qty-done:contains("3")',
    },
    {
        trigger: '.o_field_widget[name="product_id"]',
    },
    ...stepUtils.discardBarcodeForm(),
]});

registry.category("web_tour.tours").add('test_delivery_from_scratch_with_lots_1', {test: true, steps: () => [

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
    { trigger: '.o_barcode_line.o_selected .btn.o_toggle_sublines .fa-caret-down' },
    {
        trigger: '.o_add_line',
        extra_trigger: '.o_barcode_line:nth-child(2)',
    },

    {
        trigger: '.o_field_widget[name="product_id"]',
    },
    ...stepUtils.discardBarcodeForm(),
]});

registry.category("web_tour.tours").add('test_delivery_from_scratch_with_incompatible_lot', {test: true, steps: () => [
    { trigger: '.o_barcode_client_action', run: 'scan 0000000001' },
    { trigger: '.o_barcode_line:first-child .o_edit' },
    ...stepUtils.discardBarcodeForm(),
]});

registry.category("web_tour.tours").add('test_delivery_from_scratch_with_common_lots_name', {test: true, steps: () => [
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
    { trigger: '.o_barcode_line:contains("productserial1")' },
    // Open the form view to trigger a save
    { trigger: '.o_barcode_line:first-child .o_edit' },
    ...stepUtils.discardBarcodeForm(),
]});

registry.category("web_tour.tours").add('test_receipt_with_sn_1', {test: true, steps: () => [
    { trigger: '.o_barcode_client_action', run: 'scan sn1' },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_delivery_from_scratch_with_sn_1', {test: true, steps: () => [
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
        trigger: '.o_notification.border-danger'
    },

    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertErrorMessage('The scanned serial number is already used.');
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
    },

    {
        trigger: '.o_field_widget[name="product_id"]',
    },

]});

registry.category("web_tour.tours").add('test_delivery_reserved_lots_1', {test: true, steps: () => [

    {
        trigger: '.o_barcode_client_action',
        run: 'scan productlot1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot2',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot2',
    },
    // Open the form view to trigger a save
    {
        trigger: '.o_add_line',
    },

    {
        trigger: '.o_field_widget[name="product_id"]',
    },
    ...stepUtils.discardBarcodeForm(),
]});

registry.category("web_tour.tours").add('test_delivery_different_products_with_same_lot_name', {test: true, steps: () => [

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
    // Open the form view to trigger a save
    {
        trigger: '.o_add_line',
    },

    {
        trigger: '.o_field_widget[name="product_id"]',
    },
    ...stepUtils.discardBarcodeForm(),
]});

registry.category("web_tour.tours").add('test_delivery_reserved_with_sn_1', {test: true, steps: () => [
    /* scan a product tracked by serial number. Then scan 4 a its serial numbers.
    */
    {
        trigger: '.o_barcode_client_action',
        run: 'scan productserial1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn3',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn3',
    },

    {
        trigger: '.o_notification.border-danger'
    },

    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertErrorMessage('The scanned serial number is already used.');
        },
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn4',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn2',
    },
    // Open the form view to trigger a save
    {
        trigger: '.o_add_line',
    },

    {
        trigger: '.o_field_widget[name="product_id"]',
    },
    ...stepUtils.discardBarcodeForm(),
]});

registry.category("web_tour.tours").add('test_nomenclature_alias_and_conversion', {test: true, steps: () => [
    // Before all, create a new receipt on the fly.
    { trigger: '.o_stock_barcode_main_menu', run: 'scan WH-RECEIPTS' },
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

registry.category("web_tour.tours").add('test_receipt_reserved_lots_multiloc_1', {test: true, steps: () => [
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

registry.category("web_tour.tours").add('test_receipt_duplicate_serial_number', {test: true, steps: () => [
    /* Create a receipt. Try to scan twice the same serial in different
    * locations.
    */
    {
        trigger: '.o_stock_barcode_main_menu:contains("Barcode Scanning")',
    },
    // reception
    {
        trigger: '.o_stock_barcode_main_menu',
        run: 'scan WH-RECEIPTS',
    },

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
        trigger: '.o_notification.border-danger',
        run: function () {
            helper.assertErrorMessage('The scanned serial number is already used.');
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
        run: 'scan O-BTN.validate'
    },
    {
        trigger: '.o_notification.border-success',
        run: function () {
            helper.assertErrorMessage('The transfer has been validated');
        },
    },
]});

registry.category("web_tour.tours").add('test_delivery_duplicate_serial_number', {test: true, steps: () => [
    /* Create a delivery. Try to scan twice the same serial in different
    * locations.
    */
    {
        trigger: '.o_stock_barcode_main_menu',
        run: 'scan WH-DELIVERY',
    },

    {
        trigger: '.o_scan_message.o_scan_src',
        run: 'scan LOC-01-01-00',
    },

    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan productserial1',
    },

    {
        trigger: '.o_barcode_line:contains("productserial1")',
        run: 'scan sn1',
    },

    {
        trigger: '.o_barcode_line .o_line_lot_name:contains("sn1")',
        run: 'scan LOC-01-01-00',
    },

    {
        trigger: '.o_scan_message.o_scan_validate',
        run: 'scan productserial1',
    },
    { trigger: '.o_barcode_line.o_selected .btn.o_toggle_sublines .fa-caret-down' },

    {
        trigger: '.o_barcode_line:nth-child(2)',
        run: 'scan sn1',
    },

    {
        trigger: '.o_notification.border-danger',
        run: function () {
            helper.assertErrorMessage('The scanned serial number is already used.');
        },
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn2',
    },
    ...stepUtils.validateBarcodeOperation(),

    {
        trigger: '.o_stock_barcode_main_menu',
        run: function () {
            helper.assertErrorMessage('The transfer has been validated');
        },
    },
]});

registry.category("web_tour.tours").add('test_bypass_source_scan', {test: true, steps: () => [
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
    },

    {
        trigger: '.o_field_many2one[name=lot_id]',
        extra_trigger: '.o_field_widget[name="qty_done"]',
        position: "bottom",
        run: function (actions) {
            actions.text("", this.$anchor.find("input"));
        },
    },

    {
        trigger: '.o_field_widget[name=qty_done] input',
        run: 'text 0',
    },

    {
        trigger: '.o_save'
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
        trigger: '.o_notification.border-danger',
        run: function () {
            helper.assertErrorMessage("You are expected to scan one or more products or a package available at the picking location");
        },
    },
    { trigger: 'button.o_notification_close' },
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

registry.category("web_tour.tours").add('test_picking_type_mandatory_scan_settings_pick_int_1', {test: true, steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertLinesCount(2);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(false); // Can't validate until product with barcode was scanned.
            const [ lineProductNoBarcode, lineProduct1 ] = document.querySelectorAll('.o_barcode_line');
            helper.assert(
                lineProduct1.querySelector('.btn.o_edit').disabled, true,
                "Edit button should be disabled until the product was scanned");
            helper.assert(
                Boolean(lineProduct1.querySelector('.btn.o_add_quantity')), false,
                "No button to automatically add the quantity if the product scan is mandatory");
            helper.assert(
                lineProductNoBarcode.querySelector('.btn.o_edit').disabled, false,
                "Edit button is always enabled if the product has no barcode (it can't be scanned')");
            helper.assert(
                Boolean(lineProductNoBarcode.querySelector('.btn.o_add_quantity')), true,
                "Add quantity button is always displayed if the product has no barcode");
        }
    },
    // Scans the source location, it should display an error.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-01-00',
    },
    {
        trigger: '.o_notification.border-danger',
        run: function() {
            helper.assert(
                document.querySelector('.o_notification_content').innerText,
                "You must scan a product");
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
            const lineProduct1 = document.querySelector('.o_barcode_line[data-barcode="product1"]');
            helper.assert(
                lineProduct1.querySelector('.btn.o_edit').disabled, false,
                "product1 was scanned, the edit button should now be enabled");
            helper.assert(
                Boolean(lineProduct1.querySelector('.btn.o_add_quantity')), true,
                "product1 was scanned, the add quantity button should be visible");
            helper.assertValidateIsHighlighted(false);
            // Since the only product with a barcode was scanned, the validate button is enabled.
            helper.assertValidateEnabled(true);
        }
    },
    // Uses buttons to complete the lines.
    { trigger: '.o_barcode_line.o_selected .btn.o_add_quantity' },
    { trigger: '.o_barcode_line .btn.o_add_quantity' },
    // Lines are completed, the message should ask to validate the operation and that's what we do.
    {
        trigger: '.btn.o_validate_page.btn-success',
        extra_trigger: 'div[name="barcode_messages"] .fa-check-square',
    },
    { trigger: '.o_notification.border-success', isCheck: true },
    // Checks that, despite scanning set to 'no', source and destination locations are still shown
    { trigger: '.o_barcode_line:nth-child(1) .o_line_source_location:contains(".../Section 1")', isCheck: true },
    { trigger: '.o_barcode_line:nth-child(1) .o_line_destination_location:contains("WH/Stock")', isCheck: true },
    { trigger: '.o_barcode_line:nth-child(2) .o_line_source_location:contains(".../Section 1")', isCheck: true },
    { trigger: '.o_barcode_line:nth-child(2) .o_line_destination_location:contains("WH/Stock")', isCheck: true },
]});

registry.category("web_tour.tours").add('test_picking_type_mandatory_scan_settings_pick_int_2', {test: true, steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertLinesCount(2);
            helper.assertScanMessage('scan_src');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(false); // Can't validate until product with barcode was scanned.
            const [ lineProductNoBarcode, lineProduct1 ] = document.querySelectorAll('.o_barcode_line');
            helper.assert(
                lineProduct1.querySelector('.btn.o_edit').disabled, true,
                "Edit button should be disabled until the product was scanned");
            helper.assert(
                Boolean(lineProduct1.querySelector('.btn.o_add_quantity')), false,
                "No button to automatically add the quantity if the product scan is mandatory");
            helper.assert(
                lineProductNoBarcode.querySelector('.btn.o_edit').disabled, true,
                "All lines' buttons are disabled until a source location was scanned");
            helper.assert(
                lineProductNoBarcode.querySelector('.btn.o_add_quantity').disabled, true,
                "All lines' buttons are disabled until a source location was scanned");
        }
    },
    // Scans a product, it should display an error.
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    {
        trigger: '.o_notification.border-danger',
        run: function() {
            helper.assert(
                document.querySelector('.o_notification_content').innerText,
                "You are supposed to scan WH/Stock or another source location");
        },
    },
    { trigger: '.btn.o_notification_close' },

    // Scans the source location, the buttons for the product without barcode should be enabled.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-00-00',
    },
    {
        trigger: '.o_scan_message.o_scan_product',
        run: function () {
            const [ lineProductNoBarcode, lineProduct1 ] = document.querySelectorAll('.o_barcode_line');
            helper.assert(
                lineProduct1.querySelector('.btn.o_edit').disabled, true,
                "Edit button should be disabled until the product was scanned");
            helper.assert(
                Boolean(lineProduct1.querySelector('.btn.o_add_quantity')), false,
                "No button to automatically add the quantity if the product scan is mandatory");
            helper.assert(
                lineProductNoBarcode.querySelector('.btn.o_edit').disabled, false,
                "Since the source of this line was scanned and it has no barcode, its buttons should be enabled");
            helper.assert(
                lineProductNoBarcode.querySelector('.btn.o_add_quantity').disabled, false,
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
            const lineProduct1 = document.querySelector('.o_barcode_line[data-barcode="product1"]');
            helper.assert(
                lineProduct1.querySelector('.btn.o_edit').disabled, false,
                "product1 was scanned, the edit button should now be enabled");
            helper.assert(
                Boolean(lineProduct1.querySelector('.btn.o_add_quantity')), true,
                "product1 was scanned, the add quantity button should be visible");
            helper.assertValidateIsHighlighted(false);
            // Since the only product with a barcode was scanned, the validate button is enabled.
            helper.assertValidateEnabled(true);
        }
    },
    // Scans another product: it should raise an error as the destination should be scanned between each product.
    { trigger: '.o_barcode_client_action', run: 'scan product2' },
    {
        trigger: '.o_notification.border-danger',
        run: function() {
            helper.assert(
                document.querySelector('.o_notification_content').innerText,
                "Please scan destination location for product1 before scanning other product");
        },
    },
    { trigger: '.btn.o_notification_close' },

    // Uses button to complete the line, then scan the destination.
    { trigger: '.o_barcode_line.o_selected .btn.o_add_quantity' },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: 'scan LOC-01-00-00',
    },
    // Scans again product1: should raise an error as it expects the source (should be scanned after each product).
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    {
        trigger: '.o_notification.border-danger',
        run: function() {
            helper.assert(
                document.querySelector('.o_notification_content').innerText,
                "You are supposed to scan WH/Stock or another source location");
        },
    },
    { trigger: '.btn.o_notification_close' },

    // Scans the source and updates the remaining product qty with its button (because no barcode).
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-01-00',
    },
    {
        trigger: '.o_barcode_line .btn.o_add_quantity',
        extra_trigger: '.o_scan_message.o_scan_product',
    },
    // Tries to validate without scanning the destination: display a warning.
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: 'scan O-BTN.validate',
    },
    { trigger: '.o_notification.border-danger .o_notification_close.btn' },

    // Scans the destination location than validate the operation.
    {
        trigger: 'div[name="barcode_messages"] .fa-sign-in', // "Scan dest. loc." message's icon.
        run: 'scan LOC-01-00-00',
    },
    {
        trigger: '.btn.o_validate_page.btn-success',
        extra_trigger: 'div[name="barcode_messages"] .fa-check-square',
    },
    { trigger: '.o_notification.border-success', isCheck: true },
]});

registry.category("web_tour.tours").add('test_receipt_scan_package_and_location_after_group_of_product', {test: true, steps: () => [
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
        extra_trigger: ".o_barcode_line.o_selected .qty-done:contains(2)",
        trigger: ".o_barcode_line:not([data-barcode]) .o_line_button.o_add_quantity",
    },
    // ... and scans 3 productlot1 from 2 differents lots.
    { trigger: ".o_barcode_line.o_selected.o_line_completed", run: "scan productlot1" },
    { trigger: ".o_barcode_line[data-barcode='productlot1']", run: "scan lot-01" },
    { trigger: ".o_barcode_line[data-barcode='productlot1']", run: "scan lot-01" },
    { trigger: ".o_barcode_line[data-barcode='productlot1']", run: "scan lot-02" },

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
            helper.assertLineQty(0, "4 / 4");
            helper.assertLineDestinationLocation(0, ".../Section 1");

            helper.assertLineProduct(1, "product1");
            helper.assertLineQty(1, "2 / 2");
            helper.assertLineDestinationLocation(1, ".../Section 1");

            helper.assertLineProduct(2, "product1");
            helper.assertLineQty(2, "0 / 2");
            helper.assertLineDestinationLocation(2, "WH/Stock");

            helper.assertLineProduct(3, "productlot1");
            helper.assertLineQty(3, "3 / 3");
            helper.assertLineDestinationLocation(3, ".../Section 1");

            helper.assertLineProduct(4, "productlot1");
            helper.assertLineQty(4, "0 / 3");
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
            helper.assertLineQty(0, "4 / 4");
            helper.assertLineDestinationLocation(0, ".../Section 1");

            helper.assertLineProduct(1, "product1");
            helper.assertLineQty(1, "2 / 2");
            helper.assertLineDestinationLocation(1, ".../Section 1");

            helper.assertLineProduct(2, "product1");
            helper.assertLineQty(2, "0 / 2");
            helper.assertLineDestinationLocation(2, "WH/Stock");

            helper.assertLineProduct(3, "productlot1");
            helper.assertLineQty(3, "3 / 3");
            helper.assertLineDestinationLocation(3, ".../Section 1");

            helper.assertLineProduct(4, "productlot1");
            helper.assertLineQty(4, "1 / 1");
            helper.assertLineDestinationLocation(4, ".../Section 2");

            helper.assertLineProduct(5, "productlot1");
            helper.assertLineQty(5, "0 / 2");
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
            helper.assertLineQty(0, "4 / 4");
            helper.assertLineDestinationLocation(0, ".../Section 1");

            helper.assertLineProduct(1, "product1");
            helper.assertLineQty(1, "2 / 2");
            helper.assertLineDestinationLocation(1, ".../Section 1");

            let line = helper.getLine({ index: 2 });
            helper.assertLineProduct(line, "product1");
            helper.assertLineQty(line, "2 / 2");
            helper.assertLineDestinationLocation(line, ".../Section 3");
            helper.assert(line.querySelector('[name="package"]').innerText, "pack-128");

            helper.assertLineProduct(3, "productlot1");
            helper.assertLineQty(3, "3 / 3");
            helper.assertLineDestinationLocation(3, ".../Section 1");

            helper.assertLineProduct(4, "productlot1");
            helper.assertLineQty(4, "1 / 1");
            helper.assertLineDestinationLocation(4, ".../Section 2");

            line = helper.getLine({ index: 5 });
            helper.assertLineProduct(5, "productlot1");
            helper.assertLineQty(5, "2 / 2");
            helper.assertLineDestinationLocation(5, ".../Section 3");
            helper.assert(line.querySelector('[name="package"]').innerText, "pack-128");
        }
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_picking_type_mandatory_scan_complete_flux_receipt', {test: true, steps: () => [
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
    { trigger: '.o_barcode_line[data-barcode="product2"] .btn.o_add_quantity' },
    {
        trigger: '.o_barcode_line:not([data-barcode]) .btn.o_add_quantity',
        extra_trigger: '.o_barcode_line[data-barcode="product2"].o_line_completed',
    },
    // Before to scan remaining product, scans a first time the destination.
    {
        trigger: '.o_barcode_line:not([data-barcode]).o_line_completed',
        run: 'scan WH-INPUT'
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
    {
        trigger: '.o_barcode_line[data-barcode="productlot1"].o_selected',
        run: 'scan lot-001'
    },
    {
        trigger: '.o_barcode_line[data-barcode="productlot1"].o_selected',
        run: 'scan lot-002'
    },
    {
        trigger: '.o_barcode_line[data-barcode="productlot1"].o_selected',
        run: 'scan lot-002'
    },
    {
        trigger: '.o_barcode_line[data-barcode="productlot1"].o_selected',
        run: 'scan lot-003'
    },
    {
        trigger: '.o_barcode_line[data-barcode="productlot1"].o_selected',
        run: 'scan lot-003'
    },
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
    {
        trigger: '.o_barcode_line[data-barcode="productserial1"].o_selected',
        run: 'scan sn-002'
    },
    {
        trigger: '.o_barcode_line[data-barcode="productserial1"].o_selected',
        run: 'scan sn-003'
    },
    // It should ask to scan the destination, so scans it.
    {
        trigger: 'div[name="barcode_messages"] .o_scan_product_or_dest',
        run: 'scan WH-INPUT',
    },
    // Now the destination was scanned, it should say the operation can be validate.
    {
        extra_trigger: 'div[name="barcode_messages"] .o_scan_validate',
        trigger: '.o_validate_page.btn-success',
    },
    {
        trigger: '.o_notification.border-success',
        isCheck: true
    },
]});

registry.category("web_tour.tours").add('test_picking_type_mandatory_scan_complete_flux_internal', {test: true, steps: () => [
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
        trigger: '.o_notification.border-danger',
        run: function() {
            helper.assertErrorMessage(
                "Please scan destination location for product1 before scanning other product");
        },
    },
    { trigger: '.btn.o_notification_close' },

    { // Scans the destination (Section 1).
        trigger: '.o_barcode_line.o_selected',
        run: 'scan LOC-01-01-00'
    },
    // product1 line is split, 1 qty moves to Section 1, the rest is left as default
    {
        trigger: '.o_barcode_client_action',
        extra_trigger: '.o_barcode_line.o_line_completed .o_line_destination_location .fw-bold:contains("Section 1")',
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
        trigger: '.o_barcode_line:not([data-barcode]) .btn.o_add_quantity',
        extra_trigger: '.o_scan_message.o_scan_product',
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
    { trigger: '.o_barcode_line.o_selected .btn.o_toggle_sublines .fa-caret-down' },
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
        extra_trigger: 'div[name="barcode_messages"] .fa-check-square', // "Press validate" message icon.
        trigger: '.o_validate_page.btn-success',
    },
    {
        trigger: '.o_notification.border-success',
        isCheck: true,
    },
]});

registry.category("web_tour.tours").add('test_picking_type_mandatory_scan_complete_flux_pick', {test: true, steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(7);
            helper.assertScanMessage('scan_src');
            helper.assertValidateVisible(true);
            helper.assertValidateEnabled(false);
            const lineButtons = document.querySelectorAll('.btn.o_edit,.btn.o_add_quantity');
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
    { trigger: '.btn.o_notification_close' },

    // Scan another location (Section 2 for the instance).
    {
        trigger: '.o_scan_message.o_scan_src',
        run: 'scan LOC-01-02-00'
    },
    {
        trigger: '.o_line_source_location:contains(".../Section 2") .fw-bold',
        run: function() {
            helper.assertLinesCount(7);
            helper.assertScanMessage('scan_product');
            const lineProduct2 = document.querySelector('.o_barcode_line');
            helper.assert(
                lineProduct2.querySelector('.btn.o_edit').disabled, false,
                "Since the source location was scanned, its buttons should be enabled");
            helper.assert(
                lineProduct2.querySelector('.btn.o_add_quantity').disabled, false,
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
    { trigger: '.btn.o_notification_close' },

    // Scans a pack then scans again Section 3.
    { trigger: '.o_barcode_line.o_line_completed', run: 'scan cluster-pack-01' },
    { trigger: '.o_barcode_line.o_selected .result-package', run: 'scan LOC-01-01-00' },
    {
        trigger: '.o_line_source_location:contains(".../Section 1") .fw-bold',
        run: function() {
            helper.assertLinesCount(7);
            helper.assertScanMessage('scan_product');
        }
    },
    // Scans product1 from Section 1, pack it.
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    { trigger: '.o_barcode_client_action', run: 'scan cluster-pack-01' },
    // Do the same from Section 3
    { trigger: '.o_barcode_line.o_line_completed', run: 'scan shelf3' },
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: 'scan productlot1'
    },
    {
        trigger: '.o_notification',
        run: function() {
            helper.assertErrorMessage("You must scan a package or put in pack");
        },
    },
    { trigger: '.btn.o_notification_close' },
    { trigger: '.o_barcode_client_action', run: 'scan cluster-pack-01' },
    // scans lot-001 and lot-002
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed .result-package',
        run: 'scan productlot1'
    },
    // Checks we can't edit a line for a tracked product until the tracking number was scan.
    { trigger: '.o_barcode_line.o_selected .btn.o_toggle_sublines .fa-caret-down' },
    {
        trigger: '.o_barcode_line.o_selected .o_sublines',
        run: function() {
            const [ lot001Line, lot002Line ] = helper.getSublines();
            helper.assert(lot001Line.querySelector('.btn.o_add_quantity').disabled, true,
                "Lot number not scanned yet, so line's buttons are disabled.");
            helper.assert(lot002Line.querySelector('.btn.o_add_quantity').disabled, true,
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
            helper.assert(lot001Line.querySelector('.btn.o_add_quantity').disabled, false,
                "lot-001 was scanned, its line's buttons should be enable");
            helper.assert(lot002Line.querySelector('.btn.o_add_quantity').disabled, true,
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
            const lot001Line = helper.getSubline({ completed: true});
            const lot002Line = helper.getSubline({ completed: false});
            helper.assert(Boolean(lot001Line.querySelector('.btn.o_add_quantity')), false,
                "The two lot-001 were scanned, the button to add the quantity should be hidden.");
            helper.assert(lot002Line.querySelector('.btn.o_add_quantity').disabled, true);
        }
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot-002',
    },
    {
        trigger: '.o_barcode_line.o_selected .qty-done:contains(1)',
        run: function() {
            const lot002Line = document.querySelector('.o_sublines .o_barcode_line.o_selected:not(.o_line_completed)');
            helper.assert(lot002Line.querySelector('.btn.o_add_quantity').disabled, false,
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
            const lot002Line = document.querySelector('.o_sublines .o_barcode_line.o_selected.o_line_completed');
            helper.assert(Boolean(lot002Line.querySelector('.btn.o_add_quantity')), false,
                "Demand quantity was scanned, the button shouldn't be visible.");
        }
    },
    { trigger: '.o_barcode_client_action', run: 'scan cluster-pack-02' },

    // Scans Section 1 (source) and processes the remaining products.
    { trigger: '.o_barcode_line.o_selected.o_line_completed .result-package', run: 'scan LOC-01-01-00' },
    {
        extra_trigger: '.o_line_source_location:contains(".../Section 1") .fw-bold',
        trigger: '.o_barcode_line:not([data-barcode]) .btn.o_add_quantity',
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
        trigger: '.o_line_source_location:contains(".../Section 4") .fw-bold',
        extra_trigger: '.o_scan_message.o_scan_product',
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
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        extra_trigger: '.o_scan_message.o_scan_package',
        run: 'scan cluster-pack-02'
    },
    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan lot-003',
    },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: 'scan cluster-pack-02'
    },
    // It should say the operation can be validate.
    {
        extra_trigger: 'div[name="barcode_messages"] .fa-check-square', // "Press validate" message icon.
        trigger: '.o_validate_page.btn-success',
    },
    {
        trigger: '.o_notification.border-success',
        isCheck: true,
    },
]});

registry.category("web_tour.tours").add('test_picking_type_mandatory_scan_complete_flux_pack', {test: true, steps: () => [
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
    { trigger: '.o_validate_page.btn-success' },
    {
        trigger: '.o_notification',
        run: function() {
            helper.assertErrorMessage("All products need to be packed");
        },
    },
    { trigger: '.btn.o_notification_close' },
    // Puts in pack.
    { trigger: '.o_barcode_client_action', run: 'scan O-BTN.pack'},
    // Validates the operation.
    {
        extra_trigger: '.o_scan_message.o_scan_validate',
        trigger: '.o_validate_page.btn-success',
    },
    { trigger: '.o_notification.border-success', isCheck: true },
]});

registry.category("web_tour.tours").add('test_picking_type_mandatory_scan_complete_flux_delivery', {test: true, steps: () => [
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
        extra_trigger: '.o_scan_message.o_scan_validate', // "Press validate" message icon.
        trigger: '.o_barcode_line.o_line_completed',
        run: 'scan O-BTN.validate',
    },
    { trigger: '.o_notification.border-success', isCheck: true },
]});

registry.category("web_tour.tours").add('test_pack_multiple_scan', {test: true, steps: () => [

    {
        trigger: '.o_stock_barcode_main_menu:contains("Barcode Scanning")',
    },
    // Receipt
    {
        trigger: '.o_stock_barcode_main_menu',
        run: 'scan WH-RECEIPTS',
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
        trigger: '.o_barcode_line:nth-child(2)',
        run: 'scan O-BTN.pack',
    },
    ...stepUtils.validateBarcodeOperation(),

    {
        trigger: '.o_stock_barcode_main_menu',
        run: function () {
            helper.assertErrorMessage('The transfer has been validated');
        },
    },
    // Delivery transfer to check the error message
    {
        trigger: '.o_stock_barcode_main_menu',
        run: 'scan WH-DELIVERY',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan PACK0001000',
    },

    {
        trigger: '.o_barcode_line:nth-child(2)',
        run: 'scan PACK0001000',
    },

    {
        trigger: '.o_notification.border-danger'
    },

    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertErrorMessage('This package is already scanned.');
            const line1 = helper.getLine({ barcode: "product1" });
            helper.assertLineIsHighlighted(line1, true);
            const line2 = helper.getLine({ barcode: "product2" });
            helper.assertLineIsHighlighted(line2, true);
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

registry.category("web_tour.tours").add('test_pack_common_content_scan', {test: true, steps: () => [
    /* Scan 2 packages PACK1 and PACK2 that contains both product1 and
     * product 2. It also scan a single product1 before scanning both pacakges.
     * the purpose is to check that lines with a same product are not merged
     * together. For product 1, we should have 3 lines. One with PACK 1, one
     * with PACK2 and the last without package.
     */
    {
        trigger: '.o_stock_barcode_main_menu:contains("Barcode Scanning")',
    },

    {
        trigger: '.o_stock_barcode_main_menu',
        run: 'scan WH-DELIVERY',
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

registry.category("web_tour.tours").add('test_pack_multiple_location', {test: true, steps: () => [

    {
        trigger: '.o_stock_barcode_main_menu:contains("Barcode Scanning")',
    },

    {
        trigger: '.o_stock_barcode_main_menu',
        run: 'scan WH-INTERNAL',
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
        trigger: '.o_notification.border-danger',
        run: () => helper.assertLineQty(0, "1")
    },

    { trigger: '.o_package_content' },
    {
        trigger: '.o_kanban_view:contains("product1")',
        run: function () {
            helper.assertKanbanRecordsCount(2);
        },
    },
    { trigger: '.o_close' },

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

registry.category("web_tour.tours").add('test_pack_multiple_location_02', {test: true, steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-01-00'
    },

    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan PACK0002020',
    },

    {
        trigger: '.o_barcode_client_action',
        extra_trigger: '.o_barcode_line.o_selected',
        run: 'scan LOC-01-02-00',
    },

    {
        trigger: '.o_barcode_line .o_line_destination_location:contains("WH/Stock/Section 2")',
        run: 'scan O-BTN.validate',
    },

    {
        trigger: '.o_notification.border-success',
        isCheck: true,
    },
]});

registry.category("web_tour.tours").add('test_pack_multiple_location_03', {test: true, steps: () => [
    {trigger: '.o_barcode_client_action', run: 'scan shelf3'},
    {
        trigger: '.o_barcode_line',
        run: function() {
            helper.assertLinesCount(1);
            helper.assert($('.o_barcode_line .package').text(), "PACK000666");
        }
    },
    {trigger: '.o_barcode_client_action', run: 'scan product1'},
    {
        trigger: '.qty-done:contains(1)',
        run: function() {
            helper.assertLinesCount(1);
            helper.assert($('.o_barcode_lines .o_barcode_line .package').length, 0);
        }
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_put_in_pack_from_multiple_pages', {test: true, steps: () => [
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
        trigger: '.o_barcode_client_action',
        run: 'scan product1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan O-BTN.pack',
    },

    ...stepUtils.validateBarcodeOperation('.o_barcode_line:contains("PACK")'),
]});

registry.category("web_tour.tours").add('test_reload_flow', {test: true, steps: () => [
    {
        trigger: '.o_stock_barcode_main_menu',
        run: 'scan WH-RECEIPTS'
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.o_edit',
    },

    {
        extra_trigger: '.o_field_widget[name="product_id"]',
        trigger: '.o_field_widget[name=qty_done] input',
        run: 'text 2',
    },

    {
        trigger: '.o_save',
    },

    {
        trigger: '.o_add_line',
    },

    {
        trigger: ".o_field_widget[name=product_id] input",
        run: 'text product2',
    },

    {
        trigger: ".ui-menu-item > a:contains('product2')",
    },

    {
        trigger: '.o_save',
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
        extra_trigger: '.o_barcode_line:nth-child(2) .o_line_destination_location:contains(".../Section 1")',
        trigger: '.o_barcode_line:first-child()',
    },
    {
        trigger: '.o_barcode_line:first-child().o_selected',
        run: 'scan LOC-01-01-00'
    },
    {
        trigger: '.o_barcode_line:nth-child(1) .o_line_destination_location:contains(".../Section 1")',
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_highlight_packs', {test: true, steps: () => [
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

registry.category("web_tour.tours").add('test_put_in_pack_from_different_location', {test: true, steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1',
    },

    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: 'scan product2',
    },

    {
        trigger: '.o_validate_page.btn-success',
        run: 'scan O-BTN.pack',
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

registry.category("web_tour.tours").add('test_put_in_pack_before_dest', {test: true, steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-01-00',
    },

    {
        trigger: '.o_barcode_line .o_line_source_location:contains(".../Section 1") .fw-bold',
        run: 'scan product1',
    },
    { trigger: '.o_barcode_client_action', run: 'scan LOC-01-02-00' },

    {
        trigger: '.o_scan_message.o_scan_src',
        run: 'scan shelf3',
    },

    {
        trigger: '.o_barcode_line .o_line_source_location:contains(".../Section 3") .fw-bold',
        run: 'scan product2',
    },

    {
        trigger: '.o_barcode_line .qty-done:contains("1")',
        run: 'scan shelf4',
    },

    {
        trigger: '.o_scan_message.o_scan_validate',
        run: 'scan O-BTN.pack'
    },

    {
        trigger: '.modal-title:contains("Choose destination location")',
    },

    {
        trigger: '.o_field_widget[name="location_dest_id"] input',
        run: 'click',
    },
    {
        trigger: '.ui-menu-item > a:contains("Section 2")',
        auto: true,
        in_modal: false,
    },

    {
        trigger: '.o_field_widget[name="location_dest_id"]',
        run: function () {
            helper.assert(
                $('.o_field_widget[name="location_dest_id"] input').val(),
                'WH/Stock/Section 2'
            );
        },
    },

    {
        trigger: '.btn-primary',
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_put_in_pack_scan_package', {test: true, steps: () => [
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
        run: 'scan O-BTN.pack',
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
        trigger: '.o_barcode_line .o_line_source_location .fw-bold:contains("Section 2")',
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

registry.category("web_tour.tours").add('test_put_in_pack_new_lines', {test: true, steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan P00001',
    },
    {
        trigger: '.o_notification.border-danger',
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
        run: 'scan O-BTN.validate',
    },
    {
        trigger: '.o_notification.border-success',
        isCheck: true,
    },
]});

registry.category("web_tour.tours").add('test_picking_owner_scan_package', {test: true, steps: () => [
    {
        trigger: '.o_stock_barcode_main_menu:contains("Barcode Scanning")',
    },
    {
        trigger: '.o_stock_barcode_main_menu',
        run: 'scan WH-DELIVERY',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan P00001',
    },
    {
        trigger: '.o_barcode_client_action:contains("P00001")',
    },
    {
        trigger: '.o_barcode_client_action:contains("Azure Interior")',
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_receipt_delete_button', {test: true, steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2',
    },
    stepUtils.confirmAddingUnreservedProduct(),
    // ensure receipt's extra product CAN be deleted
    {
        trigger: '.o_barcode_line[data-barcode="product2"] .o_edit',
    },
    {
        trigger: '.o_field_widget[name="product_id"]',
        run: function () {
            helper.assert($('.o_delete').length, 1);
        },
    },
    {
        trigger: '.o_discard',
    },
    // ensure receipt's original move CANNOT be deleted
    {
        trigger: '.o_barcode_line:nth-child(2) .o_edit',
    },
    {
        trigger: '.o_field_widget[name="product_id"]',
        run: function () {
            helper.assert($('.o_delete').length, 0);
        },
    },
    {
        trigger: '.o_discard',
    },
    // add extra product not in original move + delete it
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product3',
    },
    stepUtils.confirmAddingUnreservedProduct(),
    {
        trigger: '.o_barcode_line[data-barcode="product3"] .o_edit',
    },
    {
        trigger: '.o_delete',
    },
    {
        trigger: '.o_validate_page',
        run: 'scan O-BTN.validate',
    }, {
        content: "check the picking is validated",
        trigger: '.o_notification.border-success',
        isCheck: true,
    },
]});

registry.category("web_tour.tours").add("test_scrap", {test: true, steps: () => [
    // Opens the receipt and checks we can't scrap if not done.
    { trigger: ".o_stock_barcode_main_menu", run: "scan receipt_scrap_test" },
    { trigger: ".o_barcode_actions" },
    {
        trigger: ".o_barcode_settings",
        run: function() {
            const scrapButton = document.querySelector("button.o_scrap");
            helper.assert(Boolean(scrapButton), false, "Scrap button shouldn't be displayed");
        },
    },
    { trigger: "button.o_close" },
    { trigger: ".o_barcode_lines", run: "scan O-BTN.scrap" },
    { trigger: ".o_notification.border-warning:contains('You can\\'t register scrap')" },
    // Process the receipt then re-opens it again.
    { trigger: ".o_line_button.o_add_quantity" },
    { trigger: ".o_validate_page.btn-success" },
    { trigger: ".o_stock_barcode_main_menu", run: "scan receipt_scrap_test" },
    {
        trigger: ".o_scan_message.o_picking_already_done",
        run: "scan O-BTN.scrap",
    },
    {
        extra_trigger: ".modal-title:contains('Scrap')",
        trigger: ".btn[special='cancel']",
    },
    { trigger: ".o_barcode_actions" },
    {
        trigger: ".o_barcode_settings",
        run: function() {
            const scrapButton = document.querySelector("button.o_scrap");
            helper.assert(Boolean(scrapButton), true, "Scrap button should be displayed");
        },
    },
    // Exits the receipt and opens the delivery.
    { trigger: "button.o_exit" },
    { extra_trigger: ".o_barcode_lines_header", trigger: "button.o_exit" },
    { trigger: ".o_stock_barcode_main_menu", run: "scan delivery_scrap_test" },
    // Checks we can scrap for a delivery.
    { trigger: ".o_barcode_actions" },
    {
        trigger: ".o_barcode_settings",
        run: function() {
            const scrapButton = document.querySelector("button.o_scrap");
            helper.assert(Boolean(scrapButton), true, "Scrap button should be displayed");
        },
    },
    { trigger: "button.o_close" },
    { trigger: ".o_barcode_lines", run: "scan O-BTN.scrap" },
    {
        extra_trigger: ".modal-title:contains('Scrap')",
        trigger: ".btn[special='cancel']",
    },
    // Process the delivery then re-opens it again.
    { trigger: ".o_line_button.o_add_quantity" },
    { trigger: ".o_validate_page.btn-success" },
    { trigger: ".o_stock_barcode_main_menu", run: "scan delivery_scrap_test" },
    { trigger: ".o_barcode_lines_header", run: "scan O-BTN.scrap" },
    { trigger: ".o_notification.border-warning:contains('You can\\'t register scrap')" },
    { trigger: ".o_barcode_actions" },
    {
        trigger: ".o_barcode_settings",
        run: function() {
            const scrapButton = document.querySelector("button.o_scrap");
            helper.assert(Boolean(scrapButton), false, "Scrap button shouldn't be displayed");
        },
    },
]});

registry.category("web_tour.tours").add("test_picking_scan_package_confirmation", {test: true, steps: () => [
    // Scan product 1
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    // Scan Package 1 to trigger the scan confirmation
    { trigger: '.o_barcode_line .qty-done:contains("1")', run: 'scan package001' },
    // Cancel the package scan
    { trigger: ".modal-content button.btn-secondary" },
    // Scan Package 1 to trigger the scan confirmation
    { trigger: '.o_barcode_line .qty-done:contains("1")', run: 'scan package001' },
    // Confirm the package scan, thus the line quantity will be increased
    { trigger: ".modal-content button.btn-primary" },
    { trigger: '.o_barcode_line .qty-done:contains("2")', isCheck: true },
]});

registry.category("web_tour.tours").add('test_show_entire_package', {test: true, steps: () => [
    { trigger: 'button.button_operations' },
    { trigger: '.o_kanban_record:contains(Delivery Orders)' },

    // Opens picking with the package level.
    { trigger: '.o_kanban_record:contains(Delivery with Package Level)' },
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
            helper.assertButtonShouldBeVisible(line, "package_content");
            helper.assert(line.querySelector('[name="package"]').innerText, "package001package001");
            helper.assertLineQty(line, "0 / 1");
        },
    },
    { trigger: '.o_line_button.o_package_content' },
    {
        trigger: '.o_kanban_view .o_kanban_record',
        run: function () {
            helper.assertKanbanRecordsCount(1);
        },
    },
    { trigger: 'button.o_close' },
    // Scans package001 to be sure no moves will be created but the package line will be done.
    { trigger: '.o_barcode_lines', run: 'scan package001' },
    {
        trigger: '.o_barcode_line:contains("1/ 1")',
        run: function () {
            helper.assertLinesCount(1);
            helper.assertScanMessage('scan_validate');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(true);
            helper.assertValidateEnabled(true);
            const line = helper.getLine();
            helper.assertLineIsHighlighted(line, false);
            helper.assertButtonShouldBeVisible(line, "package_content");
            helper.assert(line.querySelector('[name="package"]').innerText, "package001package001");
            helper.assertLineQty(line, "1 / 1");
        },
    },
    { trigger: 'button.o_exit' },

    // Opens picking with the move.
    { trigger: '.o_kanban_record:contains(Delivery with Stock Move)' },
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
            helper.assertButtonShouldBeVisible(line, "package_content", false);
            helper.assert(line.querySelector('[name="package"]').innerText, "package002");
            helper.assertLineQty(0, '0 / 2');
        },
    },
]});

registry.category("web_tour.tours").add('test_define_the_destination_package', {test: true, steps: () => [
    {
        trigger: '.o_line_button.o_add_quantity',
    },
    {
        trigger: '.o_barcode_line .qty-done:contains("1")',
        run: 'scan PACK02',
    },
    {
        extra_trigger: '.o_barcode_line:contains("PACK02")',
        trigger: '.btn.o_validate_page',
    },
    {
        trigger: '.o_notification.border-success',
        isCheck: true,
    },
]});

registry.category("web_tour.tours").add('stock_barcode_package_with_lot', {test: true, steps: () => [
    {
        trigger: "[data-menu-xmlid='stock_barcode.stock_barcode_menu']", // open barcode app
    },
    {
        trigger: ".button_inventory",
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan Lot-test' // scan lot on a new location
    },
    {
        extra_trigger: '.o_barcode_line .package:contains(Package-test)', // verify it takes the right quantity
        trigger: '.o_apply_page',
    },
    {
        trigger: '.o_notification.border-success',
        isCheck: true,
    },
]});

registry.category("web_tour.tours").add('test_scan_same_lot_different_products', {test: true, steps: () => [
    // Scanning 123 will fetch the lot 123 for the 'aaa' product and add them
    // both in the cache (the 'aaa' product and its lot.)
    {
        trigger: '.o_barcode_client_action',
        run: 'scan 123',
    },
    {
        trigger: '.o_notification.border-danger',
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

registry.category("web_tour.tours").add('test_avoid_useless_line_creation', {test: true, steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOT01',
    },
    {
        trigger: '.o_barcode_line',
        run: 'scan LOREM',
    },
    {
        trigger: '.o_notification.border-danger',
        run: function () {
            helper.assertErrorMessage('You are expected to scan one or more products.');
        },
    },
    // Open the form view to trigger a save
    { trigger: '.o_barcode_line:first-child .o_edit' },
    ...stepUtils.discardBarcodeForm(),
]});

registry.category("web_tour.tours").add('test_split_line_reservation', {test: true, steps: () => [
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
        trigger: '.o_barcode_line .o_line_source_location:contains("Section 1")',
        run: function () {
            helper.assertLinesCount(4);
            let line = helper.getLine({ barcode: 'productlot1', completed: true });
            helper.assertLineSourceLocation(line, 'WH/Stock');
            helper.assertLineQty(line, '2 / 2');
            line = helper.getLine({ barcode: 'productlot1', completed: false });
            helper.assertLineSourceLocation(line, '.../Section 1');
            helper.assertLineQty(line, '0 / 3');
        },
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan productlot1'
    },
    {
        trigger: '.o_barcode_client_action',
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
        trigger: '.o_barcode_line .o_line_source_location:contains("Section 2")',
        run: function () {
            helper.assertLinesCount(5);
        },
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan productlot1'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOT03'
    },
    {
        trigger: '.o_barcode_line .o_line_lot_name:contains("LOT03")',
        run: function () {
            const lines = helper.getLines({ barcode: 'productlot1' });
            [0, 1, 2].map(i => helper.assertLineQty(lines[i], ["2 / 2", "2 / 2", "1 / 1"][i]));
        },
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-00-00'
    },
    // scan product1 x2
    {
        trigger: '.o_barcode_client_action',
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
            [0, 1].map(i => helper.assertLineQty(lines[i], ["2 / 2", "0 / 2"][i]));
        },
    },
    // scan product1 x2 from Section 1
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
        run: 'scan LOC-01-00-00'
    },
    // scan product2 x2 from WH/Stock
    {
        trigger: '.o_barcode_client_action',
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
            [0, 1].map(i => helper.assertLineQty(lines[i], ["2 / 2", "0 / 1"][i]));
        },
    },
    // scan product2 x1 from Section 1
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2'
    },
    // trigger a save
    {
        trigger: '.o_barcode_line .o_edit',
    },
    {
        trigger: '.o_discard',
    },
    {
        trigger: '.o_validate_page',
        run: function () {
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(true);
            helper.assertValidateEnabled(true);
            // Check lines' quantity didn't change.
            let lines = helper.getLines({ barcode: 'product1' });
            [0, 1].map(i => helper.assertLineQty(lines[i], ["2 / 2", "2 / 2"][i]));
            lines = helper.getLines({ barcode: 'product2' });
            [0, 1].map(i => helper.assertLineQty(lines[i], ["2 / 2", "1 / 1"][i]));
            lines = helper.getLines({ barcode: 'productlot1' });
            [0, 1, 2].map(i => helper.assertLineQty(lines[i], ["2 / 2", "2 / 2", "1 / 1"][i]));
        },
    },
]});

registry.category("web_tour.tours").add('test_split_line_on_destination_scan', {test: true, steps: () => [
    // Scans 2x product1.
    { trigger: '.o_barcode_line', run: "scan product1"},
    { trigger: '.o_barcode_line', run: "scan product1"},
    {
        trigger: '.o_barcode_line.o_selected .qty-done:contains("2")',
        run: () => {
            helper.assertLinesCount(1);
            helper.assertLineDestinationLocation(0, "WH/Stock");
            helper.assertLineQty(0, "2 / 4");
        }
    },
    // Scans the line's destination -> The line should be splitted in two.
    { trigger: '.o_barcode_line', run: "scan LOC-01-00-00"},
    {
        trigger: '.o_barcode_line:nth-child(2)',
        run: () => {
            helper.assertLinesCount(2);
            helper.assertLineDestinationLocation(0, "WH/Stock");
            helper.assertLineDestinationLocation(1, "WH/Stock");
            helper.assertLineQty(0, "2 / 2");
            helper.assertLineQty(1, "0 / 2");
        }
    },
    // Scans remaining quantity, then shelf1 as the destination and close the receipt.
    { trigger: '.o_barcode_line', run: "scan product1" },
    { trigger: '.o_barcode_line.o_selected:not(".o_line_completed")', run: "scan product1" },
    { trigger: '.o_barcode_line.o_selected.o_line_completed', run: "scan LOC-01-01-00" },
    {
        trigger: '.o_validate_page.btn-success',
        run: () => {
            helper.assertLinesCount(2);
            helper.assertLineDestinationLocation(0, "WH/Stock");
            helper.assertLineDestinationLocation(1, ".../Section 1");
            helper.assertLineQty(0, "2 / 2");
            helper.assertLineQty(1, "2 / 2");
        }
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_split_line_on_exit_for_delivery', {test: true, steps: () => [
    // Opens the delivery and checks its lines.
    { trigger: ".o_stock_barcode_main_menu", run: "scan delivery_split_line_on_exit" },
    {
        trigger: ".o_barcode_client_action",
        run: () => {
            helper.assertLinesCount(3);
            helper.assertLineProduct(0, "product1");
            helper.assertLineQty(0, "0 / 4");
            helper.assertLineProduct(1, "product2");
            helper.assertLineQty(1, "0 / 4");
            helper.assertLineProduct(2, "product3");
            helper.assertLineQty(2, "0 / 2");
        }
    },
    // Scans 4x product1, 2x product2 and leaves the delivery without scanning product3.
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    { trigger: ".o_barcode_line.o_selected.o_line_completed", run: "scan product2" },
    { trigger: ".o_barcode_line.o_selected:not(.o_line_completed)", run: "scan product2" },
    // Leaves the delivery and re-open it directly, then checks not lines were splitted.
    { trigger: "button.o_exit" },
    { trigger: ".o_stock_barcode_main_menu", isCheck: true },
]});

registry.category("web_tour.tours").add('test_split_line_on_exit_for_receipt', {test: true, steps: () => [
    // Opens the receipt and check its lines.
    { trigger: ".o_stock_barcode_main_menu", run: "scan receipt_split_line_on_exit" },
    {
        trigger: ".o_barcode_client_action",
        run: () => {
            helper.assertLinesCount(2);
            helper.assertLineProduct(0, "product1");
            helper.assertLineQty(0, "0 / 4");
            helper.assertLineProduct(1, "product2");
            helper.assertLineQty(1, "0 / 4");
        }
    },
    // Scans 1x product1 then put in pack => Should split the line.
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    { trigger: ".o_barcode_line.o_selected", run: "scan O-BTN.pack" },
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
            helper.assertLineQty(line1, "2 / 3");
            helper.assertLineProduct(line2, "product2");
            helper.assertLineQty(line2, "1 / 4");
            helper.assertLineProduct(line3, "product1");
            helper.assertLineQty(line3, "1 / 1");
            helper.assert(line3.querySelector(".result-package").innerText, "PACK0001000")
        }
    },
    // Goes back to the main menu (that's here the uncompleted lines shoud be split.)
    { trigger: "button.o_exit" },
    // Re-opens the picking and checks uncompleted lines were split.
    { trigger: ".o_stock_barcode_main_menu", run: "scan receipt_split_line_on_exit" },
    {
        trigger: ".o_barcode_client_action",
        run: () => {
            helper.assertLinesCount(5);
            const [line1, line2, line3, line4, line5] = helper.getLines();
            helper.assertLineProduct(line1, "product1");
            helper.assertLineQty(line1, "0 / 1");
            helper.assertLineProduct(line2, "product2");
            helper.assertLineQty(line2, "0 / 3");
            helper.assertLineProduct(line3, "product1");
            helper.assertLineQty(line3, "2 / 2");
            helper.assertLineProduct(line4, "product1");
            helper.assertLineQty(line4, "1 / 1");
            helper.assert(line4.querySelector(".result-package").innerText, "PACK0001000")
            helper.assertLineProduct(line5, "product2");
            helper.assertLineQty(line5, "1 / 1");
        }
    },
]});

registry.category("web_tour.tours").add('test_split_line_on_scan', {test: true, steps: () => [
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
            [0, 1].map(i => helper.assertLineQty(i, ["0 / 3", "2 / 2"][i]));
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
            [0, 1].map(i => helper.assertLineQty(i, ["3 / 3", "2 / 2"][i]));
        },
    },
    { trigger: '.btn.o_validate_page' },
    { trigger: '.o_notification.border-success', isCheck: true },
]});

registry.category("web_tour.tours").add('test_scan_line_splitting_preserve_destination', {test: true, steps: () => [
    // Select the first (only) line
    {
        trigger: '.o_barcode_line',
        run: 'click',
    },
    {
        trigger:  '.o_barcode_line.o_selected',
        run: function () {
            helper.assertLinesCount(1);
            helper.assertLineQty(0, '0 / 5');
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
            [0, 1].map(i => helper.assertLineQty(i, ["0 / 3", "2 / 2"][i]));
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
            [0, 1].map(i => helper.assertLineQty(lines[i], ["3 / 3", "2 / 2"][i]));
            [0, 1].map(i => helper.assertLineDestinationLocation(lines[i], [".../Section 4", ".../Section 3"][i]));
        },
    },
    { trigger: '.btn.o_validate_page' },
    { trigger: '.o_notification.border-success', isCheck: true },
]});

registry.category("web_tour.tours").add('test_editing_done_picking', {
    test: true, steps: () => [
        { trigger: '.o_barcode_client_action', run: 'scan O-BTN.validate' },
        {
            trigger: '.o_notification.border-danger',
            run: function () {
                helper.assertErrorMessage("This picking is already done");
            },
        },
    ]
});

registry.category("web_tour.tours").add("test_sml_sort_order_by_product_category", { test: true, steps: () => [
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

registry.category("web_tour.tours").add('test_create_backorder_after_qty_modified', {
    test: true, steps: () => [
        { trigger: '.o_edit'},
        { trigger: '.o_increase'},
        { trigger: '.o_save'},
        { trigger: '.o_validate_page'},
        { trigger: '.modal-dialog button.btn-primary', run: 'click' },
    ]
});
