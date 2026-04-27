/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as helper from "@stock_barcode_picking_batch/../tests/tours/tour_helper_stock_barcode_picking_batch";
import { stepUtils } from "@stock_barcode/../tests/tours/tour_step_utils";

function checkState(state) {
    helper.assertLinesCount(state.linesCount);
    helper.assertScanMessage(state.scanMessage);
    helper.assertValidateVisible(state.validate.isVisible);
    helper.assertValidateIsHighlighted(state.validate.isHighlighted);
    helper.assertValidateEnabled(state.validate.isEnabled);
}

function updateState(oldState, newState) {
    const state = Object.assign({}, oldState, newState);
    state.validate = Object.assign({}, oldState.validate, newState.validate);
    return state;
}

const defaultViewState = {
    linesCount: 0,
    scanMessage: '',
    validate: {
        isEnabled: true,
        isHighlighted: false,
        isVisible: true,
    },
};
let currentViewState;

// ----------------------------------------------------------------------------
// Tours
// ----------------------------------------------------------------------------
registry.category("web_tour.tours").add('test_barcode_batch_receipt_1', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            currentViewState = updateState(defaultViewState, {
                linesCount: 5, // 6 move lines but 5 visibles as tracked by SN lines are grouped.
                scanMessage: 'scan_product',
                validate: {
                    isEnabled: true,
                    isVisible: true,
                },
            });
            checkState(currentViewState);
            const linesFromFirstPicking = helper.getLines({ index: [0, 4] });
            const linesFromSecondPicking = helper.getLines({ index: [1, 2] });
            const linesFromThirdPicking = helper.getLines({ index: 3 });
            helper.assertLinesBelongTo(linesFromFirstPicking, "picking_receipt_1");
            helper.assertLinesBelongTo(linesFromSecondPicking, "picking_receipt_2");
            helper.assertLinesBelongTo(linesFromThirdPicking, "picking_receipt_3");
        },
    },

    // Check receipt information.
    {
        trigger: '.o_barcode_header .o_title',
        run: "click",
    },
    {
        trigger: '.o_form_label:contains("State")',
        run: "click",
    },
    {
        trigger: '.o_close',
        run: "click",
    },

    // Scan product1 x4
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },
    {
        trigger: '.o_barcode_line:first-child.o_selected.o_line_completed',
        run: function() {
            currentViewState.scanMessage = 'scan_product_or_dest';
            checkState(currentViewState);
            const lines =  helper.getLines({ barcode: "product1" });
            helper.assert(lines.length, 2, "Expect 2 lines for product1");
            helper.assertLineIsHighlighted(lines[0]);
            helper.assertLineQty(lines[0], "1/1");
            helper.assertLineQty(lines[1], "0/3");
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
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },
    {
        trigger: '.o_barcode_line[data-barcode="product1"] .qty-done:contains("3")',
        run: function() {
            checkState(currentViewState);
            const lines =  helper.getLines({ barcode: "product1", completed: true });
            helper.assert(lines.length, 2, "Expect 2 lines for product1");
            helper.assertLineQty(lines[0], "1/1");
            helper.assertLineIsHighlighted(lines[0], false);
            helper.assertLineQty(lines[1], "3/3");
            helper.assertLineIsHighlighted(lines[1]);
        }
    },

    // Scan one more time the product1 -> As no more quantity is expected, it must create
    // a new line and it will take the picking id of the selected line (here, 'picking_receipt_2').
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },
    {
        trigger: '.o_barcode_line:nth-child(6)',
        run: function() {
            currentViewState.linesCount = 6;
            checkState(currentViewState);
            helper.assertLinesCount(3, { barcode: "product1" });
            const [line1, line2] = helper.getLines({ barcode: "product1", selected: false, completed: true });
            const line3 = helper.getLine({ barcode: "product1", selected: true });
            helper.assertLineQty(line1, "1/1"); // First product1 line: qty 1/1
            helper.assertLineQty(line2, "3/3"); // Second product1 line: qty 3/3
            helper.assertLineQty(line3, "1"); // Last added line: qty 1
            helper.assertLineBelongTo(line3, "picking_receipt_2");
        }
    },

    // Scan productserial1
    {
        trigger: '.o_barcode_client_action',
        run: 'scan productserial1'
    },
    {
        trigger: '.o_barcode_line:nth-child(6).o_highlight[data-barcode="productserial1"]',
        run: function() {
            currentViewState.scanMessage = 'scan_serial';
            checkState(currentViewState);
        }
    },

    // Scan two serial numbers
    {
        trigger: '.o_barcode_client_action',
        run: 'scan SN-LHOOQ'
    },
    {
        trigger: '.o_barcode_line.o_highlight[data-barcode="productserial1"]:contains("SN-LHOOQ")',
        run: function() {
            currentViewState.scanMessage = 'scan_serial';
            checkState(currentViewState);
        }
    },
    // Scan the same serial number -> Should show an warning message.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan SN-LHOOQ'
    },
    {
        trigger: '.o_notification_bar.bg-danger',
        run: "click",
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan SN-OQPAPT'
    },
    // Unfolds grouped lines for product tracked by SN.
    {
        trigger: '.o_line_button.o_toggle_sublines',
        run: "click",
    },
    {
        trigger: '.o_sublines .o_barcode_line',
        run: function() {
            currentViewState.scanMessage = 'scan_product_or_dest';
            checkState(currentViewState);
            const sublines = helper.getSublines({ barcode: "productserial1" });
            helper.assert(sublines.length, 2, "Expect 2 lines for productserial1");
            helper.assertLineQty(sublines[0], "1");
            helper.assertLineQty(sublines[1], "1");
        }
    },

    // Scan productlot1
    {
        trigger: '.o_barcode_client_action',
        run: 'scan productlot1'
    },
    {
        trigger: '.o_barcode_line.o_highlight[data-barcode="productlot1"]',
        run: function() {
            currentViewState.scanMessage = 'scan_lot';
            checkState(currentViewState);
            const lines =  helper.getLines({ barcode: "productlot1" });
            helper.assert(lines.length, 2, "Expect 2 lines for productlot1");
            const [line1, line2] = lines;
            helper.assertLineQty(line1, "0/8");
            helper.assertLineIsHighlighted(line1);
            helper.assertLineBelongTo(line1, "picking_receipt_2");
            helper.assertLineQty(line2, "0/4");
            helper.assertLineIsHighlighted(line2, false);
            helper.assertLineBelongTo(line2, "picking_receipt_3");
        }
    },

    // Scan lot0001 x4
    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot0001'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot0001'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot0001'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot0001'
    },
    {
        trigger: '.o_barcode_line.o_highlight .qty-done:contains("4")',
        run: function() {
            currentViewState.scanMessage = 'scan_lot';
            checkState(currentViewState);
            const lines =  helper.getLines({ barcode: "productlot1" });
            helper.assert(lines.length, 2, "Expect 2 lines for productlot1");
            const [line1, line2] = lines;
            helper.assertLineQty(line1, "4/8");
            helper.assertLineIsHighlighted(line1);
            helper.assertLineBelongTo(line1, "picking_receipt_2");
            helper.assertLineQty(line2, "0/4");
            helper.assertLineIsHighlighted(line2, false);
            helper.assertLineBelongTo(line2, "picking_receipt_3");
        },
    },
    // Open the view to add a line and close it immediately.
    {
        trigger: '.o_add_line',
        run: "click",
    },
    {
        trigger: '.o_discard',
        run: "click",
    },
    {
        trigger: '.o_validate_page',
        run: function() {
            checkState(currentViewState);
        },
    },

    // Create a new line for productlot1 with an another lot name...
    {
        trigger: '.o_add_line',
        run: "click",
    },
    {
        trigger: ".o_field_widget[name=product_id] input",
        run: "edit productlot1",
    },
    {
        trigger: ".ui-menu-item > a:contains('productlot1')",
        run: "click",
    },
    {
        trigger: ".o_field_widget[name=qty_done] input",
        run: "edit 0",
    },
    {
        trigger: ".o_field_widget[name=picking_id] input",
        run: "edit picking_receipt_2",
    },
    {
        trigger: ".ui-menu-item > a:contains('picking_receipt_2')",
        run: "click",
    },
    {
        trigger: ".o-autocomplete.dropdown:not(:has(.o-autocomplete--dropdown-menu))",
    },
    {
        trigger: '.o_save',
        run: "click",
    },
    {
        trigger: '.o_barcode_line.o_selected .btn.o_toggle_sublines .fa-angle-down',
        run: "click",
    },
    {
        trigger: '.o_sublines .o_barcode_line:nth-child(2).o_selected',
        run: function() {
            checkState(currentViewState);
            const groupLines = helper.getLines({ barcode: "productlot1" });
            helper.assert(groupLines.length, 2, "Expect 2 lines for productlot1");
            const sublines = helper.getSublines({ barcode: "productlot1" });
            helper.assert(sublines.length, 2, "Expect 2 sublines for productlot1");
            helper.assertLineQty(sublines[0], "4"); // Previous line (4/8).
            helper.assertLineIsHighlighted(sublines[0], false);
            helper.assertLineQty(sublines[1], "0"); // New created line.
            helper.assertLineIsHighlighted(sublines[1]);
        },
    },

    // Scans lot0002 x4
    { trigger: '.o_barcode_client_action', run: 'scan lot0002' },
    { trigger: '.o_barcode_client_action', run: 'scan lot0002' },
    { trigger: '.o_barcode_client_action', run: 'scan lot0002' },
    { trigger: '.o_barcode_client_action', run: 'scan lot0002' },
    {
        trigger: '.o_sublines .o_barcode_line.o_highlight:contains("lot0002") .qty-done:contains("4")',
        run: function() {
            const sublines = helper.getSublines({ barcode: "productlot1" });
            helper.assert(sublines.length, 2, "Expect 2 lines for productlot1");
            helper.assertLineQty(sublines[0], "4");
            helper.assertLineIsHighlighted(sublines[0], false);
            helper.assertLineQty(sublines[1], "4");
            helper.assertLineIsHighlighted(sublines[1]);
        }
    },
    // Scan again the same lot0002 x4, it should select and increment the empty line.
    { trigger: '.o_barcode_client_action', run: 'scan lot0002' },
    { trigger: '.o_barcode_client_action', run: 'scan lot0002' },
    { trigger: '.o_barcode_client_action', run: 'scan lot0002' },
    { trigger: '.o_barcode_client_action', run: 'scan lot0002' },
    {
        trigger: '.o_barcode_line.o_highlight:contains("lot0002"):contains("picking_receipt_3") .qty-done:contains("4")',
        run: function() {
            currentViewState.validate.isHighlighted = true;
            currentViewState.scanMessage = 'scan_product_or_dest';
            currentViewState.validate.isHighlighted = true;
            checkState(currentViewState);
            const lines = helper.getLines({ barcode: "productlot1" });
            helper.assert(lines.length, 2, "Expect 2 lines for productlot1");
            const [line1, line2] = lines;
            helper.assertLineQty(line1, "8/8");
            helper.assertLineIsHighlighted(line1, false);
            helper.assertLineBelongTo(line1, "picking_receipt_2");
            helper.assertLineQty(line2, "4/4");
            helper.assertLineIsHighlighted(line2);
            helper.assertLineBelongTo(line2, "picking_receipt_3");
        }
    },
    // Selects the subline with the lot0002 and scans it again, it should increment the selected line.
    {
        trigger: '.o_sublines .o_barcode_line:contains("lot0002")',
        run: "click",
    },
    {
        trigger: '.o_sublines .o_selected:contains("lot0002")',
        run: 'scan lot0002'
    },
    {
        trigger: '.o_sublines .o_barcode_line.o_highlight:contains("lot0002") .qty-done:contains("5")',
        run: function() {
            const sublines = helper.getSublines({ barcode: "productlot1" });
            helper.assert(sublines.length, 2, "Expect 2 sublines for productlot1");
            helper.assertLineQty(sublines[0], "4");
            helper.assertLineIsHighlighted(sublines[0], false);
            helper.assertLineQty(sublines[1], "5");
            helper.assertLineIsHighlighted(sublines[1]);
        }
    },
]});

registry.category("web_tour.tours").add('test_barcode_batch_delivery_1', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            currentViewState = updateState(defaultViewState, {
                linesCount: 10,
                scanMessage: 'scan_src',
            });
            checkState(currentViewState);
            const lines = helper.getLines();

            // Products comming from Section 1.
            helper.assertLineLocations(lines[0], 'WH/Stock/Section 1');
            helper.assertLineProduct(lines[0], 'product1');

            helper.assertLineLocations(lines[1], 'WH/Stock/Section 1');
            helper.assertLineProduct(lines[1], 'product1');

            helper.assertLineLocations(lines[2], 'WH/Stock/Section 1');
            helper.assertLineProduct(lines[2], 'product4');

            helper.assertLineLocations(lines[3], 'WH/Stock/Section 1');
            helper.assertLineProduct(lines[3], 'productserial1');
            helper.assertLineTrackingNumber(lines[3], '');

            // Products coming from Section 2.
            helper.assertLineLocations(lines[4], 'WH/Stock/Section 2');
            helper.assertLineProduct(lines[4], 'product2');

            // Products coming from Section 3.
            helper.assertLineLocations(lines[5], 'WH/Stock/Section 3');
            helper.assertLineProduct(lines[5], 'product2');

            helper.assertLineLocations(lines[6], 'WH/Stock/Section 3');
            helper.assertLineProduct(lines[6], 'product3');

            // Products coming from Section 4.
            helper.assertLineLocations(lines[7], 'WH/Stock/Section 4');
            helper.assertLineProduct(lines[7], 'product4');

            // Products coming from Section 5.
            helper.assertLineLocations(lines[8], 'WH/Stock/Section 5');
            helper.assertLineProduct(lines[8], 'product5');

            helper.assertLineLocations(lines[9], 'WH/Stock/Section 5');
            helper.assertLineProduct(lines[9], 'product5');

            // Checks each line belong to the right picking.
            helper.assertLinesBelongTo([lines[0], lines[4], lines[5]], "picking_delivery_1");
            helper.assertLinesBelongTo([lines[1], lines[2], lines[6], lines[7]], "picking_delivery_2");
            helper.assertLinesBelongTo([lines[8], lines[9]], "picking_delivery_package");
            helper.assertLineBelongTo(lines[3], 'picking_delivery_sn');
        },
    },
    // Scans the source (Section 1) then scans product1 x2, product4 x1
    { trigger: '.o_barcode_client_action', run: 'scan LOC-01-01-00' },
    {
        trigger: '.o_barcode_location_line:contains("WH/Stock/Section 1").text-bg-800',
    },
    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan product1'
    },
    {
        trigger: '.o_barcode_line:nth-child(2).o_line_completed ',
        run: 'scan product1'
    },
    {
        trigger: '.o_barcode_line:nth-child(3).o_line_completed ',
        run: 'scan product4'
    },

    // Scan wrong SN -> Replace the reserved one (sn1) by sn2.
    {
        trigger: '.o_barcode_line:nth-child(4).o_line_completed ',
        run: 'scan sn2'
    },

    // Scans the next source (Section 2)
    {
        trigger: ".o_barcode_line:nth-child(5).o_line_completed ",
    },
    {
        trigger: '.o_scan_message.o_scan_product_or_src',
        run: 'scan LOC-01-02-00'
    },
    // Scan product2 x2
    {
        trigger: '.o_barcode_location_line:contains("WH/Stock/Section 2").text-bg-800',
        run: 'scan product2' // Must complete the line from Section 2.
    },
    {
        trigger: '.o_barcode_location_line.text-bg-800+.o_barcode_line.o_selected.o_line_completed',
        run: function() {
            const lines = helper.getLines();
            helper.assertLinesBelongTo([lines[4], lines[5]], 'picking_delivery_1');
            helper.assertLineLocations(lines[4], 'WH/Stock/Section 2');
            helper.assertLineLocations(lines[5], 'WH/Stock/Section 3');
        }
    },
    // Scans again product2 but it's reserved in Section 3 and we're still in Section 2 and scaning
    // the location is mandatory. So the application should ask to scan the location to confirm.
    { trigger: ".o_barcode_client_action", run: "scan product2" },
    {
        trigger: ".o_notification:has(.o_notification_bar.bg-danger):contains('Scan the current location to confirm that.')",
        run: "scan LOC-01-02-00",
    },
    { trigger: ".o_scan_message:contains('Scan a product from Section 2')", run: "scan product2" },
    {
        trigger: ".o_barcode_line[data-barcode='product2']:nth-child(3).o_selected.o_line_completed",
        run: function () {
            currentViewState.scanMessage = 'scan_product_or_src';
            checkState(currentViewState);
            const lines = helper.getLines();
            helper.assertLinesBelongTo([lines[4], lines[5]], 'picking_delivery_1');
            helper.assertLineLocations(lines[4], 'WH/Stock/Section 2');
            helper.assertLineLocations(lines[5], 'WH/Stock/Section 2');
        },
    },

    // Scans next source location (Section 3)
    { trigger: '.o_barcode_client_action', run: 'scan shelf3' },

    // Scan product3 x2
    {
        trigger: '.o_barcode_location_line:contains("WH/Stock/Section 3").text-bg-800',
        run: 'scan product3'
    },
    { trigger: ".o_barcode_line[data-barcode='product3'].o_selected", run: 'scan product3' },

    // Scans next source location (Section 4)
    {
        trigger: ".o_barcode_line[data-barcode='product3'].o_selected.o_line_completed",
        run: 'scan shelf4'
    },

    // Scan product4 x1
    {
        trigger: '.o_barcode_location_line:contains("WH/Stock/Section 4").text-bg-800',
        run: 'scan product4'
    },

    // Change the location for shelf 5 (the last one).
    {
        trigger: ".o_barcode_location_line[data-location='WH/Stock/Section 4']+.o_barcode_line.o_selected.o_line_completed",
        run: 'scan shelf5'
    },

    // Scan p5pack01 which is attended.
    {
        trigger: ".o_barcode_location_line[data-location='WH/Stock/Section 5'].text-bg-800",
        run: 'scan p5pack01'
    },
    // Scan p5pack02 which isn't attended.
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: 'scan p5pack02'
    },

    {
        trigger: '.o_barcode_line:contains("p5pack02")',
        run: function () {
            currentViewState.linesCount = 11;
            currentViewState.scanMessage = 'scan_product_or_src';
            checkState(currentViewState);
            const lines = helper.getLines();
            const line1 = lines[8]; // no pack, qty 0/4
            const line2 = lines[9]; // p5pack01, qty 4/4
            const line3 = lines[10]; // p5pack02, qty 4
            helper.assertLineQty(line1, "0/4");
            helper.assertLineQty(line2, "4/4");
            helper.assertLineQty(line3, "4");
            helper.assert(line1.querySelector('[name="package"]>span').innerText, "p5pack01 ?");
            helper.assert(line2.querySelector('[name="package"]>span').innerText, "p5pack01");
            helper.assert(line3.querySelector('[name="package"]>span').innerText, "p5pack02");
        },
    },
    {
        trigger: '.o_validate_page',
        run: "click",
    },
    // Should display the backorder's dialog, checks its content.
    {
        trigger: '.o_barcode_backorder_dialog',
        run: function() {
            const backorderLines = document.querySelectorAll(".o_barcode_backorder_product_row");
            helper.assert(backorderLines.length, 1);
            const backorderLine = backorderLines[0];
            helper.assert(backorderLine.querySelector('[name="product"]').innerText, "product5");
            helper.assert(backorderLine.querySelector('[name="qty-done"]').innerText, "0");
            helper.assert(backorderLine.querySelector('[name="reserved-qty"]').innerText, "4");
        }
    },
    {
        trigger: '.o_barcode_backorder_dialog .btn.btn-primary',
        run: "click",
    },
    { trigger: '.o_notification_bar.bg-success'},
]});

registry.category("web_tour.tours").add('test_barcode_batch_delivery_2_move_entire_package', { steps: () => [
    // Should have 3 lines: 2 for product2 (one by picking) and 1 for the package pack1.
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertScanMessage('scan_product_or_package');;
            // Line for product2, delivery 1.
            helper.assertLineBelongTo(0, 'delivery_1');
            helper.assertButtonIsVisible(0, 'package_content', false);
            helper.assertLineQty(0, '0/5');
            // Line for product2, delivery 2.
            helper.assertLineBelongTo(1, 'delivery_2');
            helper.assertButtonIsVisible(1, 'package_content', false);
            helper.assertLineQty(1, '0/5');
            // Package line for delivery 1.
            helper.assertLineBelongTo(2, 'delivery_1');
            helper.assertButtonIsVisible(2, 'package_content');
            helper.assertLineQty(2, '0/1');
        }
    },

    // Scans pack1 => Completes the corresponding package line.
    { trigger: '.o_barcode_client_action', run: 'scan pack1' },
    {
        trigger: '.o_barcode_line:nth-child(3).o_line_completed',
        run: function() {
            helper.assertLineQty(2, '1/1');
        }
    },

    // Scans pack2 => Completes the two lines waiting for it.
    { trigger: '.o_barcode_client_action', run: 'scan pack2' },
    {
        trigger: '.o_barcode_line.o_selected:nth-child(2)',
    },
    {
        trigger: '.o_barcode_line.o_selected:nth-child(1)',
        run: function() {
            helper.assertLineQty(0, '5/5');
            helper.assertLineQty(1, '5/5');
        }
    },
]});

registry.category("web_tour.tours").add('test_barcode_batch_scan_lots', { steps: () => [
    // RECEIPT PART:
    // Open the batch receipt by scanning it.
    { trigger: '.o_stock_barcode_main_menu', run: 'scan test_barcode_batch_scan_lots - receipt' },
    // Scan productlot1 then 3x lot1
    { trigger: '.o_barcode_line', run: 'scan productlot1' },
    { trigger: '.o_barcode_line.o_selected', run: 'scan lot1' },
    { trigger: '.o_barcode_line.o_selected', run: 'scan lot1' },
    { trigger: '.o_barcode_line.o_selected', run: 'scan lot1' },
    {
        trigger: '.o_barcode_line.o_selected .qty-done:contains(3)',
        run: function () {
            helper.assertLinesCount(2);
            helper.assertLineBelongTo(0, "receipt_1");
            helper.assertLineBelongTo(1, "receipt_2");
            helper.assertLineQty(0, "3/4");
            helper.assertLineQty(1, "0/4");
        },
    },
    // Now scan 1x lot2. It should create a new line for receipt_1 since the line is uncompleted.
    { trigger: '.o_barcode_client_action', run: 'scan lot2' },
    // Scan again 2x lot2. It should increment the receipt_2 line now the receipt_1 line is complete
    { trigger: '.o_barcode_line.o_selected.o_line_completed', run: 'scan lot2' },
    { trigger: '.o_barcode_line.o_selected:not(.o_line_completed)', run: 'scan lot2' },
    {
        trigger: '.o_barcode_line.o_selected .qty-done:contains(2)',
        run: function () {
            helper.assertLinesCount(2);
            helper.assertLineBelongTo(0, "receipt_1");
            helper.assertLineBelongTo(1, "receipt_2");
            helper.assertLineQty(0, "4/4");
            helper.assertLineQty(1, "2/4");
        },
    },
    // Scan 2x lot3 to complete the batch.
    { trigger: '.o_barcode_client_action', run: 'scan lot3' },
    { trigger: '.o_barcode_client_action', run: 'scan lot3' },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed .o_line_button.o_toggle_sublines',
        run: 'click',
    },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed .o_sublines',
        run: function () {
            helper.assertLinesCount(2);
            helper.assertSublinesCount(2);
            const sublines = helper.getSublines();
            helper.assertLineBelongTo(0, "receipt_1");
            helper.assertLineBelongTo(1, "receipt_2");
            helper.assertLineQty(0, "4/4");
            helper.assertLineQty(1, "4/4");
            helper.assertLineQty(sublines[0], "2");
            helper.assertLineQty(sublines[1], "2");
            helper.assertLinesTrackingNumbers(sublines, ["lot2", "lot3"]);
        },
    },
    { trigger: '.o_barcode_client_action', run: 'scan OBTVALI' },
    { trigger: '.o_notification_bar.bg-success' },

    // DELIVERY PART:
    // Now, open the batch delivery.
    { trigger: '.o_stock_barcode_main_menu', run: 'scan test_barcode_batch_scan_lots - delivery' },
    {
        trigger: '.o_barcode_line',
        run: function () {
            helper.assertLinesCount(2);
            const lines = helper.getLines();
            helper.assertLineBelongTo(0, "delivery_1");
            helper.assertLineBelongTo(1, "delivery_2");
            helper.assertLineQty(0, "0/3");
            helper.assertLineQty(1, "0/3");
            helper.assertLinesTrackingNumbers(lines, ["", ""]);
        },
    },
    // First, scan productlot1. The first line (for delivery_1) should be selected.
    { trigger: '.o_barcode_client_action', run: 'scan productlot1' },
    // Then, scan lot which is reserved for delivery_2 but will be assigned to
    // delivery_1 since it's its line who is selected.
    { trigger: '.o_barcode_line.o_selected', run: 'scan lot2' },
    // Then, scan lot3 which isn't reserved and scan again lot2 to complete delivery_1.
    { trigger: '.o_barcode_line.o_selected', run: 'scan lot3' },
    { trigger: '.o_barcode_line.o_selected', run: 'scan lot2' },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed .o_line_button.o_toggle_sublines',
        run: 'click',
    },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed .o_sublines',
        run: function () {
            helper.assertLinesCount(2);
            helper.assertSublinesCount(2);
            const sublines = helper.getSublines();
            helper.assertLineBelongTo(0, "delivery_1");
            helper.assertLineBelongTo(3, "delivery_2");
            helper.assertLineQty(0, "3/3");
            helper.assertLineQty(3, "0/3");
            helper.assertLineQty(sublines[0], "2");
            helper.assertLineQty(sublines[1], "1");
            helper.assertLinesTrackingNumbers(sublines, ["lot2", "lot3"]);
        },
    },
    // Scan lot1, lot2 and lot3 to complete delivery_2.
    { trigger: '.o_barcode_client_action', run: 'scan lot2' },
    { trigger: '.o_barcode_line.o_selected:not(.o_line_completed)', run: 'scan lot1' },
    { trigger: '.o_barcode_client_action', run: 'scan lot3' },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed .o_line_button.o_toggle_sublines',
        run: 'click',
    },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed .o_sublines',
        run: function () {
            const sublines = helper.getSublines();
            helper.assertLineBelongTo(0, "delivery_1");
            helper.assertLineBelongTo(1, "delivery_2");
            helper.assertLineQty(0, "3/3");
            helper.assertLineQty(1, "3/3");
            helper.assertLineQty(sublines[0], "1");
            helper.assertLineQty(sublines[1], "1");
            helper.assertLineQty(sublines[2], "1");
            helper.assertLinesTrackingNumbers(sublines, ["lot2", "lot1", "lot3"]);
        },
    },
    { trigger: '.o_barcode_client_action', run: 'scan OBTVALI' },
    { trigger: '.o_notification_bar.bg-success' },
]});

registry.category("web_tour.tours").add("test_barcode_batch_scan_other_reserved_lost", { steps: () => [
    { trigger: ".o_stock_barcode_main_menu", run: "scan delivery batch" },
    { trigger: ".o_barcode_line button.o_toggle_sublines", run: "click" },
    {
        trigger: ".o_barcode_line .o_sublines .o_barcode_line:first-child.o_selected",
        run: () => {
            const sublines = helper.getSublines();
            const selectedSubline = helper.getSubline({ selected: true });
            helper.assert(sublines[0], selectedSubline, "First lot should be selected");
            helper.assertLinesTrackingNumbers(sublines, ["lot1", "lot2", "lot3", ""]);
        }
    },
    // Scan lot2 one time: second line (lot2 line) should be selected.
    { trigger: ".o_barcode_line", run: "scan lot2" },
    // Scan lot2 three more time
    { trigger: ".o_sublines .o_barcode_line:nth-child(2).o_selected", run: "scan lot2" },
    { trigger: ".o_barcode_line", run: "scan lot2" },
    { trigger: ".o_barcode_line", run: "scan lot2" },
    {
        trigger: ".o_sublines .o_barcode_line:last-child.o_selected",
        run: () => {
            const sublines = helper.getSublines();
            const selectedSubline = helper.getSubline({ selected: true });
            helper.assertLineTrackingNumber(sublines[1], "lot2");
            helper.assertLineQty(sublines[1], "3/3");
            helper.assertLineTrackingNumber(sublines[3], "lot2");
            helper.assertLineQty(sublines[3], "1/1");
            helper.assert(sublines[3], selectedSubline, "Last lot should be selected");
        }
    },
    // Scan lot3: should select the 3th line.
    { trigger: ".o_barcode_line", run: "scan lot3" },
    // Scan lot1: should select the 1st line.
    { trigger: ".o_barcode_line .qty-done:contains(5)", run: "scan lot1" },
    // Scan again lot3: should re-select the 3th line.
    { trigger: ".o_sublines .o_barcode_line:first-child.o_selected", run: "scan lot3" },
    // Scan lot3 and lot1 once again to complete the delivery.
    { trigger: ".o_barcode_line .qty-done:contains(7)", run: "scan lot3" },
    { trigger: ".o_sublines .o_barcode_line:contains(3).o_line_completed" },
    { trigger: ".o_put_in_pack", run: "click" },
    {
        trigger: ".o_barcode_line .result-package", run: "scan lot1",
    },
    { trigger: ".o_barcode_line", run: "scan lot1" },
    {
        trigger: ".o_barcode_line .qty-done:contains(10)",
        run: () => {
            const sublines = helper.getSublines();
            helper.assertLineTrackingNumber(sublines[0], "lot1");
            helper.assertLineQty(sublines[0], "2/2");
            helper.assertLineTrackingNumber(sublines[1], "lot1");
            helper.assertLineQty(sublines[1], "1/1");
            helper.assertLineTrackingNumber(sublines[2], "lot2");
            helper.assertLineQty(sublines[2], "3/3");
            helper.assertLineTrackingNumber(sublines[3], "lot3");
            helper.assertLineQty(sublines[3], "3/3");
            helper.assertLineTrackingNumber(sublines[4], "lot2");
            helper.assertLineQty(sublines[4], "1/1");

        }
    },
    { trigger: ".o_validate_page.btn-primary", run: "click" },
    { trigger: ".o_stock_barcode_main_menu" },
]});

registry.category("web_tour.tours").add('test_batch_create', { steps: () => [
    { trigger: '.o_button_operations', run: "click" },
    { trigger: '.o_barcode_picking_type:contains("Delivery Orders")', run: "click" },
    { trigger: '.o_batch_picking a', run: "click" },
    { trigger: '.o_batch_picking a.active' },
    { trigger: '.o-kanban-button-new', run: "click" },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan lovelybarcode',
    },
    {
        trigger: '.o_notification:has(.bg-danger):contains("This batch transfer is still in draft, scans are disabled until the batch is confirmed") .o_notification_close',
        run: 'click',
    },
    // select 2 delivery orders
    {
        trigger: '.o_barcode_line_title:contains("picking_delivery_1")',
        run: "click",
    },
    {
        trigger: '.o_highlight .o_barcode_line_title:contains("picking_delivery_1")',
    },
    {
        trigger: '.o_barcode_line_title:contains("picking_delivery_2")',
        run: "click",
    },
    {
        trigger: '.o_highlight .o_barcode_line_title:contains("picking_delivery_2")',
    },
    {
        trigger: '.o_confirm',
        run: "click",
    },

    // from here should be the same as test_barcode_batch_delivery_1 => just check that it initially looks the same
    {
        trigger: '.o_picking_label',
        run: function () {
            currentViewState = updateState(defaultViewState, {
                linesCount: 7,
                scanMessage: 'scan_src',
            });
            checkState(currentViewState);
            const lines = helper.getLines();

            // Products comming from Section 1.
            helper.assertLineLocations(lines[0], "WH/Stock/Section 1");
            helper.assertLineProduct(lines[0], "product1");

            helper.assertLineLocations(lines[1], "WH/Stock/Section 1");
            helper.assertLineProduct(lines[1], "product1");

            helper.assertLineLocations(lines[2], "WH/Stock/Section 1");
            helper.assertLineProduct(lines[2], "product4");

            // Products coming from Section 2.
            helper.assertLineLocations(lines[3], "WH/Stock/Section 2");
            helper.assertLineProduct(lines[3], "product2");

            // Products coming from Section 3.
            helper.assertLineLocations(lines[4], "WH/Stock/Section 3");
            helper.assertLineProduct(lines[4], "product2");

            helper.assertLineLocations(lines[5], "WH/Stock/Section 3");
            helper.assertLineProduct(lines[5], "product3");

            // Products coming from Section 4.
            helper.assertLineLocations(lines[6], "WH/Stock/Section 4");
            helper.assertLineProduct(lines[6], "product4");

            // Checks each line belong to the right picking.
            helper.assertLinesBelongTo([lines[0], lines[3], lines[4]], "picking_delivery_1");
            helper.assertLinesBelongTo([lines[1], lines[2], lines[5], lines[6]], "picking_delivery_2");
        },
    },
    {
        content: "Check we did not lose the config and that scans are working",
        trigger: ".o_scan_message.o_scan_src",
        run: "scan LOC-01-01-00",
    },
    {
        trigger: ".o_scan_message.o_scan_product",
    },
]});

registry.category("web_tour.tours").add('test_put_in_pack_scan_suggested_package', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            currentViewState = updateState(defaultViewState, {
                linesCount: 5,
                scanMessage: 'scan_src',
            });
            checkState(currentViewState);
            const lines = helper.getLines();

            // Products comming from Section 1.
            helper.assertLineLocations(lines[0], "WH/Stock/Section 1");
            helper.assertLineProduct(lines[0], "product1");

            helper.assertLineLocations(lines[1], "WH/Stock/Section 1");
            helper.assertLineProduct(lines[1], "product1");

            helper.assertLineLocations(lines[2], "WH/Stock/Section 1");
            helper.assertLineProduct(lines[2], "product3");

            // Products coming from Section 2.
            helper.assertLineLocations(lines[3], "WH/Stock/Section 2");
            helper.assertLineProduct(lines[3], "product2");

            helper.assertLineLocations(lines[4], "WH/Stock/Section 2");
            helper.assertLineProduct(lines[4], "product2");

            // Checks each line belong to the right picking.
            helper.assertLinesBelongTo([lines[0], lines[2], lines[3]], "test_delivery_1");
            helper.assertLinesBelongTo([lines[1], lines[4]], "test_delivery_2");
        },
    },

    // Scans the source (Section 1), the delivery 1 line's product and put it in pack.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-01-00',
    },
    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan product1',
    },
    {
        trigger: '.o_barcode_line:nth-child(2).o_selected.o_line_completed',
        run: 'scan OBTPACK',
    },
    {
        trigger: '.o_barcode_line:contains("test_delivery_1"):contains("PACK")',
        run: function() {
            const [, line2, line3, line4, ] = helper.getLines();
            helper.assert(line2.querySelector('[name=package]').innerText, 'PACK0000001 ?'); // Display suggested package.
            helper.assert(line3.querySelector('[name=package]').innerText, 'PACK0000001');
            helper.assert(line4.querySelector('[name=package]').innerText, 'PACK0000001 ?'); // Display suggested package.
        }
    },
    // Selects product3's line then scans PACK0000001 and product3.
    {
        trigger: '.o_barcode_line[data-barcode="product3"]',
        run: "click",
    },
    { trigger: '.o_selected[data-barcode="product3"]', run: 'scan PACK0000001' },
    { trigger: '.o_selected .result-package', run: 'scan product3' },
    {
        trigger: '.o_line_completed[data-barcode="product3"]',
        run: function() {
            const [, line2, line3, line4, ] = helper.getLines();
            helper.assert(line2.querySelector('[name=package]').innerText, 'PACK0000001');
            helper.assert(line3.querySelector('[name=package]').innerText, 'PACK0000001');
            helper.assert(line4.querySelector('[name=package]').innerText, 'PACK0000001 ?'); // Display suggested package.
        }
    },

    // Scans the delivery 2 line's product and put it in pack.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1',
    },
    {
        trigger: '.o_barcode_line[data-barcode="product1"].o_selected.o_line_completed',
        run: 'scan OBTPACK',
    },
    {
        trigger: '.o_barcode_line:contains("test_delivery_2"):contains("PACK")',
        run: function() {
            const [line1, line2, line3, line4, line5] = helper.getLines();
            helper.assert(line1.querySelector('[name=package]').innerText, 'PACK0000001');
            helper.assert(line2.querySelector('[name=package]').innerText, 'PACK0000001');
            helper.assert(line3.querySelector('[name=package]').innerText, 'PACK0000002');
            helper.assert(line4.querySelector('[name=package]').innerText, 'PACK0000001 ?'); // Display suggested package.
            helper.assert(line5.querySelector('[name=package]').innerText, 'PACK0000002 ?'); // Display suggested package.
        }
    },

    // Scans the next source location (Section 2).
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-02-00',
    },
    // Scans the delivery 1 line's product and put it in pack.
    {
        trigger: '.o_barcode_location_line[data-location="WH/Stock/Section 2"].text-bg-800',
        run: 'scan product2',
    },
    {
        trigger: '.o_barcode_line[data-barcode="product2"].o_selected.o_line_completed',
        run: 'scan PACK0000001',
    },
    {
        trigger: '.o_barcode_line.o_selected:contains("PACK0000001"):not(:contains("?"))',
        run: function() {
            const [line1, line2, line3, line4, line5] = helper.getLines();
            helper.assert(line1.querySelector('[name=package]').innerText, 'PACK0000001');
            helper.assert(line2.querySelector('[name=package]').innerText, 'PACK0000001');
            helper.assert(line3.querySelector('[name=package]').innerText, 'PACK0000002');
            helper.assert(line4.querySelector('[name=package]').innerText, 'PACK0000001');
            helper.assert(line5.querySelector('[name=package]').innerText, 'PACK0000002 ?'); // Display suggested package.
        }
    },

    // Scans the delivery 2 line's product and put it in pack.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2',
    },
    {
        trigger: '.o_barcode_line:nth-child(3).o_selected.o_line_completed',
        run: 'scan PACK0000002',
    },
    {
        trigger: '.o_scan_message.o_scan_validate',
        run: function() {
            const [line1, line2, line3, line4, line5] = helper.getLines();
            helper.assert(line1.querySelector('[name=package]').innerText, 'PACK0000001');
            helper.assert(line2.querySelector('[name=package]').innerText, 'PACK0000001');
            helper.assert(line3.querySelector('[name=package]').innerText, 'PACK0000002');
            helper.assert(line4.querySelector('[name=package]').innerText, 'PACK0000001');
            helper.assert(line5.querySelector('[name=package]').innerText, 'PACK0000002');
        }
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_pack_and_same_product_several_sml', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan P00001',
    },
    {
        trigger: '.qty-done:contains("3")',
        run: function() {
            const lines =  helper.getLines({ barcode: "product1", selected: true });
            helper.assert(lines.length, 2);
            helper.assertLineQty(lines[0], "3/3");
            helper.assertLineQty(lines[1], "7/7");
        },
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan P00001',
    },
    {
        trigger: '.o_notification_bar.bg-danger',
        run: function () {
            helper.assertErrorMessage('This package is already scanned.');
        },
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan P00002',
    },
    {
        trigger: '.qty-done:contains("25")',
        run: function() {
            const lines =  helper.getLines({ barcode: "product2", selected: true });
            helper.assert(lines.length, 3);
            helper.assertLineQty(lines[0], "25/25");
            helper.assertLineQty(lines[1], "30/30");
            helper.assertLineQty(lines[2], "45");
        },
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_setting_group_lines_by_product', { steps: () => [
    // First, checks all lines are correctly grouped.
    {
        trigger: ".o_barcode_client_action",
        run: function() {
            const [line1, line2, line3, line4, line5] = helper.getLines();
            helper.assertLinesCount(5);
            // First line: 6 product1 (1 receipt1 + 2 receipt2 + 3 receipt3)
            helper.assertLineProduct(line1, "product1");
            helper.assertLineQty(line1, "0/6");
            helper.assertButtonIsVisible(line1, "toggle_sublines");
            // Second line: 5 product2 (receipt2)
            helper.assertLineProduct(line2, "product2");
            helper.assertLineQty(line2, "0/5");
            helper.assertButtonIsVisible(line2, "toggle_sublines", false);
            // Third line: 53.2 product3 (4.4 receipt1 + 48.8 receipt2)
            // Verifies that floating-point addition is correctly rounded: 4.4 + 48.8 must display
            // as 53.2 and not as a precision error like 53.199999999999996.
            helper.assertLineProduct(line3, "product3");
            helper.assertLineQty(line3, "0/53.2");
            helper.assertButtonIsVisible(line3, "toggle_sublines");
            // Fourth line: 6 productlot1 (4 receipt1 + 2 receipt2)
            helper.assertLineProduct(line4, "productlot1");
            helper.assertLineQty(line4, "0/6");
            helper.assertButtonIsVisible(line4, "toggle_sublines");
            // Fifth line: 2 product1 (receipt3, goes to Shelf2)
            helper.assertLineProduct(line5, "product1");
            helper.assertLineDestinationLocation(line5, ".../Section 2");
            helper.assertLineQty(line5, "0/2");
            helper.assertButtonIsVisible(line5, "toggle_sublines", false);
        }
    },
    // Check quantity for each pickings' line is visible also for tracked product.
    {
        trigger: ".o_barcode_line:nth-child(4) .o_toggle_sublines",
        run: "click",
    },
    {
        trigger: ".o_barcode_line.o_selected .o_sublines .o_barcode_line",
        run: function() {
            helper.assertSublinesCount(2);
            const selectedLine = helper.getLine({ selected: true});
            helper.assertLineProduct(selectedLine, "productlot1");
            const sublines = helper.getSublines();
            // receipt1
            helper.assertLineQty(sublines[0], "0/4");
            helper.assertLineBelongTo(sublines[0], "receipt1");
            // receipt2
            helper.assertLineQty(sublines[1], "0/2");
            helper.assertLineBelongTo(sublines[1], "receipt2");
        }
    },
    // Unfolds the first grouped line.
    {
        trigger: ".o_barcode_line:first-child .o_toggle_sublines",
        run: "click",
    },
    {
        trigger: ".o_barcode_line:first-child.o_selected .o_sublines .o_barcode_line",
        run: function() {
            helper.assertSublinesCount(3);
            const sublines = document.querySelectorAll(".o_sublines .o_barcode_line");
            // receipt1
            helper.assertLineQty(sublines[0], "0/1");
            helper.assertLineBelongTo(sublines[0], "receipt1");
            // receipt2
            helper.assertLineQty(sublines[1], "0/2");
            helper.assertLineBelongTo(sublines[1], "receipt2");
            // receipt3
            helper.assertLineQty(sublines[2], "0/3");
            helper.assertLineBelongTo(sublines[2], "receipt3");
        }
    },
    // Scan 2x product1 -> receipt1 line should be completed, receipt2 line should be ongoing.
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    {
        trigger: ".o_sublines .o_barcode_line.o_line_completed",
    },
    {
        trigger: ".o_sublines .o_barcode_line.o_selected.o_line_not_completed",
        run: function() {
            helper.assertSublinesCount(3);
            const sublines = document.querySelectorAll(".o_sublines .o_barcode_line");
            // receipt1
            helper.assertLineQty(sublines[0], "1/1");
            helper.assertLineBelongTo(sublines[0], "receipt1");
            // receipt2
            helper.assertLineQty(sublines[1], "1/2");
            helper.assertLineBelongTo(sublines[1], "receipt2");
            // receipt3
            helper.assertLineQty(sublines[2], "0/3");
            helper.assertLineBelongTo(sublines[2], "receipt3");
        }
    },
    // Scan 4x product1 to complete the first line.
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    {
        trigger: ".o_barcode_location_group > .o_barcode_line.o_line_completed",
        run: function() {
            helper.assertSublinesCount(3);
            const sublines = document.querySelectorAll(".o_sublines .o_barcode_line");
            // receipt1
            helper.assertLineQty(sublines[0], "1/1");
            helper.assertLineBelongTo(sublines[0], "receipt1");
            // receipt2
            helper.assertLineQty(sublines[1], "2/2");
            helper.assertLineBelongTo(sublines[1], "receipt2");
            // receipt3
            helper.assertLineQty(sublines[2], "3/3");
            helper.assertLineBelongTo(sublines[2], "receipt3");
        }
    },
    // Scans two more times product1 -> The last line (the not grouped one) should be selected.
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    { trigger: ".o_barcode_line.o_selected.o_line_not_completed", run: "scan product1" },
    {
        trigger: ".o_barcode_line.o_selected.o_line_completed",
        run: function() {
            const line = helper.getLine({ selected: true });
            helper.assertLineQty(line, "2/2");
            helper.assertLineProduct(line, "product1");
            helper.assertLineBelongTo(line, "receipt3");
        }
    },
    // Scans one last time product1 -> An extra line is created using current selected picking and
    // default locations. The added line should be grouped with other ones too.
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    {
        trigger: ".o_barcode_line.o_selected.o_line_not_completed",
        run: function() {
            const groupedLine = helper.getLine({ selected: true });
            const selectedSubline = helper.getSubline({ selected: true });
            helper.assertLineQty(groupedLine, "7/6");
            helper.assertLineProduct(groupedLine, "product1");
            helper.assertLineQty(selectedSubline, "1");
            helper.assertLineBelongTo(selectedSubline, "receipt3");
        }
    },
    // Scans 2x product2.
    { trigger: ".o_barcode_client_action", run: "scan product2" },
    { trigger: ".o_barcode_client_action", run: "scan product2" },
    {
        trigger: ".o_barcode_line[data-barcode='product2'].o_selected .qty-done:contains(2)",
        run: function() {
            const line = helper.getLine({ selected: true });
            helper.assertLineQty(line, "2/5");
            helper.assertLineProduct(line, "product2");
            helper.assertLineBelongTo(line, "receipt2");
        }
    },
    // Adds through the form view another line for product2 in receipt3.
    {
        trigger: ".o_add_line",
        run: "click",
    },
    {
        trigger: "#picking_id_0",
        run: "edit receipt"
    },
    {
        trigger: "a.dropdown-item:contains('receipt3')",
        run: "click",
    },
    {
        trigger: "#product_id_0",
        run: "edit Test",
    },
    {
        trigger: "input#product_id_0",
        run: "edit product2",
    },
    {
        trigger: "a.dropdown-item:contains('product2')",
        run: "click",
    },
    {
        trigger: ".o_field_widget[name='product_id'] input:value('product2')",
    },
    {
        trigger: "button.o_save",
        run: "click",
    },
    // Checks the added line is grouped with the one from receipt2
    {
        trigger: ".o_barcode_line.o_selected .o_toggle_sublines",
        run: "click",
    },
    {
        trigger: ".o_barcode_line.o_selected .o_sublines .o_barcode_line",
        run: function() {
            helper.assertSublinesCount(2);
            const sublines = document.querySelectorAll(".o_sublines .o_barcode_line");
            // receipt2
            helper.assertLineQty(sublines[0], "2/5");
            helper.assertLineBelongTo(sublines[0], "receipt2");
            // receipt3 (added line)
            helper.assertLineQty(sublines[1], "1");
            helper.assertLineBelongTo(sublines[1], "receipt3");
        }
    },
    // Process productlot1.
    { trigger: ".o_barcode_client_action", run: "scan productlot1" },
    { trigger: ".o_barcode_line[data-barcode='productlot1'].o_selected", run: "scan lot1" },
    { trigger: ".o_barcode_client_action", run: "scan lot1" },
    { trigger: ".o_barcode_client_action", run: "scan lot2" },
    { trigger: ".o_barcode_client_action", run: "scan lot2" },
    { trigger: ".o_barcode_client_action", run: "scan lot3" },
    { trigger: ".o_barcode_client_action", run: "scan lot3" },
    {
        trigger: ".o_barcode_line.o_selected.o_line_completed .o_toggle_sublines",
        run: "click",
    },
    {
        trigger: ".o_barcode_line.o_selected .o_sublines .o_barcode_line",
        run: function() {
            helper.assertSublinesCount(3);
            const sublines = document.querySelectorAll(".o_sublines .o_barcode_line");
            // lot1 receipt1
            helper.assertLineQty(sublines[0], "2/4");
            helper.assertLineBelongTo(sublines[0], "receipt1");
            // lot2 receipt1
            helper.assertLineQty(sublines[1], "2");
            helper.assertLineBelongTo(sublines[1], "receipt1");
            // lot3 receipt2
            helper.assertLineQty(sublines[2], "2/2");
            helper.assertLineBelongTo(sublines[2], "receipt2");
        }
    },
]})

registry.category("web_tour.tours").add("test_setting_group_lines_by_product_when_tracking_is_off", {
    steps: () => [
        { trigger: ".o_barcode_line button.o_toggle_sublines", run: "click" },
        {
            trigger: ".o_sublines > .o_barcode_line",
            run: () => {
                helper.assertLinesCount(1);
                helper.assertSublinesCount(2);
                helper.assertLineProduct(0, "product1");
            }
        },
    ],
});

registry.category("web_tour.tours").add('test_split_line_on_exit_for_batch', { steps: () => [
    // Opens the batch and check its lines.
    { trigger: ".o_stock_barcode_main_menu", run: "scan batch_split_line_on_exit" },
    {
        trigger: ".o_barcode_client_action",
        run: () => {
            helper.assertLinesCount(2);
            helper.assertLineProduct(0, "product1");
            helper.assertLineQty(0, "0/4");
            helper.assertLineBelongTo(0, "receipt1");
            helper.assertLineProduct(1, "product2");
            helper.assertLineQty(1, "0/4");
            helper.assertLineBelongTo(1, "receipt2");
        }
    },
    // Scans 2x product1 and 1x product2 and goes back to the main menu.
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    { trigger: ".o_barcode_line.o_selected", run: "scan product1" },
    { trigger: ".o_barcode_client_action", run: "scan product2" },
    {
        trigger: ".o_barcode_line.o_selected[data-barcode='product2']",
        run: () => {
            helper.assertLinesCount(2);
            helper.assertLineProduct(0, "product1");
            helper.assertLineQty(0, "2/4");
            helper.assertLineBelongTo(0, "receipt1");
            helper.assertLineProduct(1, "product2");
            helper.assertLineQty(1, "1/4");
            helper.assertLineBelongTo(1, "receipt2");
        }
    },
    // Goes back to the main menu (that's here the uncompleted lines shoud be split.)
    {
        trigger: "button.o_exit",
        run: "click",
    },
    // Re-opens the batch and checks uncompleted lines were split.
    { trigger: ".o_stock_barcode_main_menu", run: "scan batch_split_line_on_exit" },
    {
        trigger: ".o_barcode_client_action",
        run: () => {
            helper.assertLinesCount(4);
            const [line1, line2, line3, line4] = helper.getLines();
            helper.assertLineProduct(line1, "product1");
            helper.assertLineQty(line1, "0/2");
            helper.assertLineBelongTo(line1, "receipt1");
            helper.assertLineProduct(line2, "product2");
            helper.assertLineQty(line2, "0/3");
            helper.assertLineBelongTo(line2, "receipt2");
            helper.assertLineProduct(line3, "product1");
            helper.assertLineQty(line3, "2/2");
            helper.assertLineBelongTo(line3, "receipt1");
            helper.assertLineProduct(line4, "product2");
            helper.assertLineQty(line4, "1/1");
            helper.assertLineBelongTo(line4, "receipt2");
        }
    },
]});

registry.category("web_tour.tours").add("test_scan_can_change_destination_location", { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-01-00',
    },
    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan product1',
    },
    { trigger: '.o_barcode_line.o_selected.o_line_completed' },
    {
        trigger: '.o_barcode_line:not(.o_selected) button.o_add_remaining_quantity',
        run: "click",
    },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: 'scan shelf3',
    },
    {
        trigger: '.o_validate_page.btn.btn-primary',
        run: 'click',
    },
]});

registry.category("web_tour.tours").add("test_pack_batch_in_multiple_packages", {
    steps: () => [
        {
            trigger: ".o_barcode_client_action",
            run: () => {
                helper.assertLinesCount(4);
                helper.assertLineProduct(0, "product1");
                helper.assertLineQty(0, "0/2");
                helper.assertLineBelongTo(0, "Lovely receipt 1");
                helper.assertLineProduct(1, "product1");
                helper.assertLineQty(1, "0/3");
                helper.assertLineBelongTo(1, "Lovely receipt 2");
                helper.assertLineProduct(2, "product2");
                helper.assertLineQty(2, "0/2");
                helper.assertLineBelongTo(2, "Lovely receipt 1");
                helper.assertLineProduct(3, "product2");
                helper.assertLineQty(3, "0/3");
                helper.assertLineBelongTo(3, "Lovely receipt 2");
            }
        },
        {
            trigger: ".o_barcode_line:has(.o_product_label:contains(product1)):has(.o_picking_label:contains('Lovely receipt 1'))",
            run: "scan product1",
        },
        {
            trigger: ".o_barcode_line:has(.o_product_label:contains(product1)):has(.o_picking_label:contains('Lovely receipt 1')):has(.qty-done:contains(1))",
            run() {},
        },
        {
            trigger: ".o_barcode_line:has(.o_product_label:contains(product1)):has(.o_picking_label:contains('Lovely receipt 2')) .o_add_remaining_quantity",
            run: "click",
        },
        {
            trigger: ".o_put_in_pack",
            run: "click",
        },
        {
            trigger: ".o_barcode_line .result-package",
            run: () => {
                helper.assertLinesCount(5);
                const [line1, line2, line3, line4, line5] = helper.getLines();
                const packageName = line5.querySelector('[name=package]').innerText
                helper.assertLineProduct(0, "product1");
                helper.assertLineQty(0, "0/1");
                helper.assertLineBelongTo(0, "Lovely receipt 1");
                helper.assert(line1.querySelector('[name=package]').innerText, `${packageName} ?`); // Display suggested package.
                helper.assertLineProduct(1, "product2");
                helper.assertLineQty(1, "0/2");
                helper.assertLineBelongTo(1, "Lovely receipt 1");
                helper.assert(line2.querySelector('[name=package]').innerText, `${packageName} ?`); // Display suggested package.
                helper.assertLineProduct(2, "product2");
                helper.assertLineQty(2, "0/3");
                helper.assertLineBelongTo(2, "Lovely receipt 2");
                helper.assert(line3.querySelector('[name=package]').innerText, `${packageName} ?`); // Display suggested package.
                helper.assertLineProduct(3, "product1");
                helper.assertLineQty(3, "1/1");
                helper.assertLineBelongTo(3, "Lovely receipt 1");
                helper.assert(line4.querySelector('[name=package]').innerText, packageName);
                helper.assertLineProduct(4, "product1");
                helper.assertLineQty(4, "3/3");
                helper.assertLineBelongTo(4, "Lovely receipt 2");
                helper.assert(line5.querySelector('[name=package]').innerText, packageName);
            }
        },
        {
            trigger: ".o_barcode_line:has(.o_product_label:contains(product1)):has(.o_picking_label:contains('Lovely receipt 1')) .o_add_remaining_quantity",
            run: "click",
        },
        {
            trigger: ".o_barcode_line:has(.o_product_label:contains(product2)):has(.o_picking_label:contains('Lovely receipt 1')) .o_add_remaining_quantity",
            run: "click",
        },
        {
            trigger: ".o_barcode_line:has(.o_product_label:contains(product2)):has(.o_picking_label:contains('Lovely receipt 2')) .o_add_remaining_quantity",
            run: "click",
        },
        {
            trigger: ".o_barcode_lines:not(:has(.o_barcode_line:contains(product1) .o_add_remaining_quantity))",
            run() {},
        },
        {
            trigger: ".o_put_in_pack",
            run: "click",
        },
        {
            trigger: ".o_barcode_lines:not(:contains(?))",
            run: () => {
                helper.assertLinesCount(5);
                const [line1, line2, line3, line4, line5] = helper.getLines();
                const package1 = line1.querySelector('[name=package]').innerText
                const package2 = line3.querySelector('[name=package]').innerText
                helper.assertLineProduct(0, "product1");
                helper.assertLineQty(0, "1/1");
                helper.assertLineBelongTo(0, "Lovely receipt 1");
                helper.assert(line1.querySelector('[name=package]').innerText, package1);
                helper.assertLineProduct(1, "product1");
                helper.assertLineQty(1, "3/3");
                helper.assertLineBelongTo(1, "Lovely receipt 2");
                helper.assert(line2.querySelector('[name=package]').innerText, package1);
                helper.assertLineProduct(2, "product1");
                helper.assertLineQty(2, "1/1");
                helper.assertLineBelongTo(2, "Lovely receipt 1");
                helper.assert(line3.querySelector('[name=package]').innerText, package2);
                helper.assertLineProduct(3, "product2");
                helper.assertLineQty(3, "2/2");
                helper.assertLineBelongTo(3, "Lovely receipt 1");
                helper.assert(line4.querySelector('[name=package]').innerText, package2);
                helper.assertLineProduct(4, "product2");
                helper.assertLineQty(4, "3/3");
                helper.assertLineBelongTo(4, "Lovely receipt 2");
                helper.assert(line5.querySelector('[name=package]').innerText, package2);
            }
        },
        ...stepUtils.validateBarcodeOperation(),
    ],
});

registry.category("web_tour.tours").add("test_barcode_batch_partial_receipt_leave_reopen", {
    steps: () => [
        // Scan the product once for picking_receipt_1
        {
            trigger: '.o_barcode_line:contains(picking_receipt_1):contains(product1)',
            run: 'click',
        },
        {
            trigger: '.o_barcode_line:contains(product1)',
            run: 'scan product1',
        },
        // Scan the product twice for picking_receipt_2
        {
            trigger: '.o_barcode_line:contains(picking_receipt_2):contains(product1)',
            run: 'click',
        },
        {
            trigger: '.o_barcode_line:contains(product1)',
            run: 'scan product1',
        },
        {
            trigger: '.o_barcode_line:contains(product1)',
            run: 'scan product1',
        },
        // We need additional steps to make sure the python code is called
        {
            trigger: '.o_exit',
            run: 'click',
        },
        {
            trigger: '.o_button_operations',
            run: 'click',
        },
    ]
});

registry.category("web_tour.tours").add("test_barcode_batch_GS1_scan_barcode_with_new_serial", {
    steps: () => [
        {
            trigger: '.o_barcode_line:contains(product2)',
            run: 'scan product2',
        },
        {
            trigger: '.o_barcode_line:contains(productserial1)',
            run: 'scan 012345678901234410BATCHSN1',
        },
        ...stepUtils.validateBarcodeOperation(),
    ]
});
