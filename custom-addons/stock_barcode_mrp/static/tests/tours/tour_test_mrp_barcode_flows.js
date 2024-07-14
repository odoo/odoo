/** @odoo-module */

import helper from '@stock_barcode/../tests/tours/tour_helper_stock_barcode';
import { registry } from "@web/core/registry";
import { stepUtils } from '@stock_barcode/../tests/tours/tour_step_utils';

registry.category("web_tour.tours").add('test_immediate_receipt_kit_from_scratch_with_tracked_compo', {test: true, steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan kit_lot',
    },
    {
        trigger: '.o_barcode_line:contains("Kit Lot") .o_edit',
    },
    {
        trigger: '.o_digipad_button.o_increase',
    },
    {
        trigger: '.o_save',
    },
    {
        trigger: '.o_barcode_line:contains("Kit Lot") .o_add_quantity'
    },
    {
        trigger: '.o_barcode_line:contains("Kit Lot") .qty-done:contains("3")',
        run: 'scan simple_kit',
    },
    {
        extra_trigger: '.o_barcode_line:contains("Simple Kit")',
        trigger: '.btn.o_validate_page',
    },
    {
        extra_trigger: '.o_notification.border-danger',
        trigger: '.o_barcode_line:contains("Compo Lot")',
        run: function() {
            helper.assertLinesCount(4);
            const [ kit_lot_compo01, simple_kit_compo01, simple_kit_compo02, kit_lot_compo_lot ] = document.querySelectorAll('.o_barcode_line');
            helper.assertLineProduct(kit_lot_compo01, 'Compo 01');
            helper.assertLineProduct(kit_lot_compo_lot, 'Compo Lot');
            helper.assertLineProduct(simple_kit_compo01, 'Compo 01');
            helper.assertLineProduct(simple_kit_compo02, 'Compo 02');
        }
    },
    {
        trigger: '.o_barcode_line:contains("Compo Lot")',
        run: 'scan compo_lot',
    },
    {
        trigger: '.o_barcode_line.o_selected div[name="lot"] .o_next_expected',
        run: 'scan super_lot',
    },
    ...stepUtils.validateBarcodeOperation('.o_line_lot_name:contains("super_lot")'),
]});

registry.category("web_tour.tours").add('test_planned_receipt_kit_from_scratch_with_tracked_compo', {test: true, steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan kit_lot',
    },
    {
        trigger: '.o_barcode_line:contains("Kit Lot") .o_edit',
    },
    {
        trigger: '.o_digipad_button.o_increase',
    },
    {
        trigger: '.o_save',
    },
    {
        trigger: '.o_barcode_line:contains("Kit Lot") .o_add_quantity'
    },
    {
        trigger: '.o_barcode_line:contains("Kit Lot") .qty-done:contains("3")',
        run: 'scan simple_kit',
    },
    {
        extra_trigger: '.o_barcode_line:contains("Simple Kit")',
        trigger: '.btn.o_validate_page',
    },
    {
        extra_trigger: '.o_notification.border-danger',
        trigger: '.o_barcode_line:contains("Compo Lot")',
        run: function() {
            helper.assertLinesCount(4);
            const [ kit_lot_compo01, simple_kit_compo01, simple_kit_compo02, kit_lot_compo_lot ] = document.querySelectorAll('.o_barcode_line');
            helper.assertLineProduct(kit_lot_compo01, 'Compo 01');
            helper.assertLineProduct(kit_lot_compo_lot, 'Compo Lot');
            helper.assertLineProduct(simple_kit_compo01, 'Compo 01');
            helper.assertLineProduct(simple_kit_compo02, 'Compo 02');
        }
    },
    {
        trigger: '.o_barcode_line:contains("Compo Lot")',
    },
    {
        trigger: '.o_selected:contains("Compo Lot")',
        run: 'scan super_lot',
    },
    ...stepUtils.validateBarcodeOperation('.o_line_lot_name:contains("super_lot")'),
]});

registry.category("web_tour.tours").add('test_process_confirmed_mo', {test: true, steps: () => [
    {
        trigger: '.o_kanban_card_header:contains("Manufacturing")',
    },
    {
        trigger: '.oe_kanban_card:contains("Final Product")',
    },
    {
        trigger: '.o_title.navbar-text:contains("WH/MO")',
    },
    {
        trigger: '.o_header .o_barcode_line_title:contains("Final Product")',
        extra_trigger: '.o_barcode_line_title:contains("Compo 01")',
    },
    {
        trigger: 'button[name="produceButton"]',
    },
    {
        trigger: '.o_header_completed .qty-done:contains("1")',
        extra_trigger: '.o_line_completed',
    },
    {
        trigger: 'div[data-barcode="compo01"] .qty-done:contains("2")',
    },
    {
        extra_trigger: '.o_scan_message.o_scan_validate',
        trigger: '.o_validate_page',
    },
    {
        trigger: '.o_notification.border-success',
        isCheck: true,
    },
]});

registry.category("web_tour.tours").add('test_barcode_production_create', {test: true, steps: () => [
    { trigger: ".o_kanban_card_header:contains('Manufacturing')" },
    { trigger: ".o-kanban-button-new" },
    // Scans final product, it should create the header line for this product.
    {
        trigger: '.o_title.navbar-text:contains("New")',
        extra_trigger: '.o_scan_message.o_scan_product',
        run: 'scan final',
    },
    {
        trigger: ".o_barcode_line.o_header",
        run: function() {
            helper.assert(helper.getLines().length, 1, "The header's line should be the only line");
            const headerLine = helper.getLine();
            helper.assertLineProduct(headerLine, "Final Product");
            helper.assertLineQty(headerLine, "0 / 1");
        }
    },
    // Scans components, it should create a line for the component, then increases its quantity.
    { trigger: ".o_scan_message.o_scan_component", run: "scan compo01" },
    {
        trigger: ".o_barcode_line.o_selected",
        run: function() {
            helper.assert(helper.getLines().length, 2);
            const headerLine = helper.getLine({ index: 0 });
            const componentLine = helper.getLine({ barcode: "compo01" });
            helper.assertLineQty(headerLine, "0 / 1");
            helper.assertLineQty(componentLine, "1");
        }
    },
    { trigger: ".o_barcode_client_action", run: 'scan compo01' },
    {
        trigger: ".o_barcode_line.o_selected .qty-done:contains('2')",
        run: function() {
            helper.assert(helper.getLines().length, 2);
            const headerLine = helper.getLine({ index: 0 });
            const componentLine = helper.getLine({ barcode: "compo01" });
            helper.assertLineQty(headerLine, "0 / 1");
            helper.assertLineQty(componentLine, "2");
        }
    },
    // Scans the final product again, it should increase the header line's quantity.
    { trigger: ".o_barcode_client_action", run: 'scan final' },
    {
        trigger: ".o_header_completed .qty-done:contains('1')",
        run: function() {
            helper.assert(helper.getLines().length, 2);
            const headerLine = helper.getLine({ index: 0 });
            helper.assertLineQty(headerLine, "1 / 1");
        }
    },
    { trigger: ".o_barcode_client_action", run: 'scan final' },
    {
        trigger: ".o_header_completed .qty-done:contains('2')",
        run: function() {
            helper.assert(helper.getLines().length, 2);
            const headerLine = helper.getLine({ index: 0 });
            helper.assertLineQty(headerLine, "2 / 1");
        }
    },
    ...stepUtils.validateBarcodeOperation(".o_scan_message.o_scan_validate"),
]});

registry.category("web_tour.tours").add("test_barcode_production_create_bom", {test: true, steps: () => [
    // Creates a new production from the Barcode App.
    { trigger: ".o_kanban_card_header:contains('Manufacturing')" },
    { trigger: ".o-kanban-button-new" },
    // Scans a product with BoM, it should add it as the final product and add a line for each components.
    {
        trigger: ".o_title.navbar-text:contains('New')",
        extra_trigger: ".o_scan_message.o_scan_product",
        run: "scan final",
    },
    {
        trigger: ".o_barcode_line.o_header",
        run: function() {
            const lines = helper.getLines();
            helper.assert(lines.length, 3, "The header line + 2 components lines");
            const [headerLine, componentLine1, componentLine2] = lines;
            helper.assertLineProduct(headerLine, "Final Product");
            helper.assertLineQty(headerLine, "0 / 1");
            helper.assertLineProduct(componentLine1, "Compo 01");
            helper.assertLineQty(componentLine1, "0 / 2");
            helper.assertLineProduct(componentLine2, "Compo 02");
            helper.assertLineQty(componentLine2, "0 / 3");
        }
    },
    // Scans again the finished product, it should increase its quantity and its components' quantity aswell.
    { trigger: ".o_barcode_client_action", run: 'scan final' },
    {
        trigger: ".o_barcode_line.o_header.o_header_completed",
        run: function() {
            const lines = helper.getLines();
            helper.assert(lines.length, 3, "The header line + 2 components lines");
            const [headerLine, componentLine1, componentLine2] = lines;
            helper.assertLineProduct(headerLine, "Final Product");
            helper.assertLineQty(headerLine, "1 / 1");
            helper.assertLineProduct(componentLine1, "Compo 01");
            helper.assertLineQty(componentLine1, "2 / 2");
            helper.assertLineProduct(componentLine2, "Compo 02");
            helper.assertLineQty(componentLine2, "3 / 3");
        }
    },
    // Scans two more times the final product and validate the production.
    { trigger: ".o_barcode_client_action", run: 'scan final' },
    { trigger: ".o_barcode_client_action", run: 'scan final' },
    {
        trigger: ".o_barcode_line.o_header .qty-done:contains(3)",
        run: function() {
            const lines = helper.getLines();
            helper.assert(lines.length, 3, "The header line + 2 components lines");
            const [headerLine, componentLine1, componentLine2] = lines;
            helper.assertLineProduct(headerLine, "Final Product");
            helper.assertLineQty(headerLine, "3 / 1");
            helper.assertLineProduct(componentLine1, "Compo 01");
            helper.assertLineQty(componentLine1, "6 / 2");
            helper.assertLineProduct(componentLine2, "Compo 02");
            helper.assertLineQty(componentLine2, "9 / 3");
        }
    },
    ...stepUtils.validateBarcodeOperation(".o_scan_message.o_scan_validate"),
]})

registry.category("web_tour.tours").add('test_barcode_production_create_tracked_bom', {test: true, steps: () => [
    {
        trigger: '.o_kanban_card_header:contains("Manufacturing")',
    },
    {
        trigger: '.o-kanban-button-new',
    },
    {
        trigger: '.o_title.navbar-text:contains("New")',
        extra_trigger: '.o_scan_message.o_scan_product',
        run: 'scan final_lot',
    },
    {
        trigger: '.o_header .o_barcode_line_title:contains("Final Product2")',
        extra_trigger: '.o_scan_message.o_scan_component',
    },
    {
        trigger: 'div[data-barcode="compo01"] .o_barcode_scanner_qty:contains("2")',
        extra_trigger: 'div[data-barcode="compo_lot"] .o_barcode_scanner_qty:contains("2")'
    },
    {
        trigger: '.o_header .o_line_button.o_edit',
    },
    {
        trigger: '.o_button_qty_done',
    },
    {
        trigger: 'div[name="product_qty"] .o_input',
        run: 'text 3',
    },
    {
        trigger: 'button[name="change_prod_qty"]',
    },
    {
        extra_trigger: 'span[name="product_uom_qty"]:contains("3")',
        trigger: '.o_save',
    },
    {
        trigger: 'div[data-barcode="compo01"] .o_barcode_scanner_qty:contains("3")',
        extra_trigger: '.o_header .o_barcode_scanner_qty:contains("3")',
    },
    {
        trigger: 'div[data-barcode="compo_lot"] .o_barcode_scanner_qty:contains("3")',
        extra_trigger: '.o_scan_message.o_scan_component',
        run: 'scan compo01',
    },
    {
        trigger: 'div[data-barcode="compo01"].o_selected .qty-done:contains("1")',
        run: 'scan compo01',
    },
    {
        trigger: 'div[data-barcode="compo01"].o_selected .qty-done:contains("2")',
        run: 'scan compo01',
    },
    {
        trigger: 'div[data-barcode="compo01"].o_selected.o_line_completed .qty-done:contains("3")',
        run: 'scan compo_lot',
    },
    {
        trigger: '.o_scan_message.o_scan_lot',
        run: 'scan lot01',
    },
    {
        trigger: 'div[data-barcode="compo_lot"].o_selected .qty-done:contains("1")',
        run: 'scan lot01',
    },
    {
        trigger: 'div[data-barcode="compo_lot"].o_selected .qty-done:contains("2")',
        run: 'scan lot01',
    },
    {
        trigger: '.o_by_products',
        extra_trigger: 'div[data-barcode="compo_lot"].o_selected.o_line_completed .qty-done:contains("3")'
    },
    {
        trigger: '.o_add_byproduct',
        run: function() {
            const viewByProductsBtn = document.querySelectorAll('.o_by_products');
            const addLineBtn = document.querySelectorAll('.o_add_line');
            const produceBtn = document.querySelectorAll('.o_validate_page');
            helper.assert(viewByProductsBtn.length, 0, 'By product buttons must be hidden');
            helper.assert(addLineBtn.length, 0, 'Add line button must be hidden');
            helper.assert(produceBtn.length, 0, 'Produce button must be hidden');
        }
    },
    {
        trigger: '.o_add_byproduct',
    },
    {
        trigger: 'div[name="product_id"] .o_input',
        run: 'text By Product',
    },
    {
        trigger: '.dropdown-item:contains("By Product")',
    },
    {
        trigger: 'div[name="qty_done"] .o_input',
        run: 'text 2',
    },
    {
        trigger: '.o_save',
    },
    {
        trigger: '.o_barcode_line_title:contains("By Product")',
        extra_trigger: '.qty-done:contains("2")',
    },
    {
        trigger: '.o_save_byproduct',
    },
    {
        trigger: '.o_scan_message.o_scan_final_product',
        run: 'scan final_lot',
    },
    {
        trigger: '.o_scan_message.o_scan_lot',
        run: 'scan lot02',
    },
    {
        trigger: '.o_header .qty-done:contains("1")',
        run: 'scan lot02',
    },
    {
        trigger: '.o_header .qty-done:contains("2")',
        run: 'scan lot02',
    },
    {
        extra_trigger: '.o_header_completed',
        trigger: '.o_scan_message.o_scan_validate',
    },
    ...stepUtils.validateBarcodeOperation(".o_validate_page.btn-success"),
]});

registry.category("web_tour.tours").add("test_barcode_production_reserved_from_multiple_locations", {test: true, steps: () => [
    {
        trigger: ".o_barcode_client_action",
        run: function() { // Check all lines are here (header + 4 compos)
            const lines = helper.getLines();
            helper.assert(lines.length, 5, "The header line + 4 components lines");
            const [headerLine, line1, line2, line3, line4] = lines;
            helper.assertLineProduct(headerLine, "Final Product");
            helper.assertLineQty(headerLine, "0 / 3");
            helper.assertLineProduct(line1, "Compo 01");
            helper.assertLineSourceLocation(line1, ".../Section 1")
            helper.assertLineQty(line1, "0 / 1");
            helper.assertLineProduct(line2, "Compo 01");
            helper.assertLineQty(line2, "0 / 2");
            helper.assertLineSourceLocation(line2, ".../Section 2")
            helper.assertLineProduct(line3, "Compo 01");
            helper.assertLineQty(line3, "0 / 2");
            helper.assertLineSourceLocation(line3, ".../Section 3")
            helper.assertLineProduct(line4, "Compo 01");
            helper.assertLineQty(line4, "0 / 1");
            helper.assertLineSourceLocation(line4, ".../Section 4")
        }
    },
    // Scans Shelf 1, Comp 01, Shelf 2 and Comp 01 again.
    {
        trigger: ".o_scan_message.o_scan_src",
        run: "scan LOC-01-01-00",
    },
    {
        trigger: ".o_scan_message.o_scan_component",
        run: "scan compo01",
    },
    {
        trigger: ".o_barcode_line.o_selected.o_line_completed",
        extra_trigger: ".o_scan_message.o_scan_component",
        run: "scan LOC-01-02-00",
    },
    {
        trigger: ".o_barcode_line:nth-child(3) .o_highlight .o_line_source_location",
        run: "scan compo01",
    },
    // Scans the final product a first time.
    {
        trigger: ".o_barcode_line:nth-child(3).o_selected",
        run: "scan final",
    },
    {
        trigger: ".o_barcode_line:nth-child(3):not(.o_selected)",
        run: function() { // Check all lines are here (header + 4 compos)
            const lines = helper.getLines();
            helper.assert(lines.length, 5, "The header line + 4 components lines");
            const [headerLine, line1, line2, line3, line4] = lines;
            helper.assertLineProduct(headerLine, "Final Product");
            helper.assertLineQty(headerLine, "1 / 3");
            helper.assertLineProduct(line1, "Compo 01");
            helper.assertLineSourceLocation(line1, ".../Section 1")
            helper.assertLineQty(line1, "1 / 1");
            helper.assertLineProduct(line2, "Compo 01");
            helper.assertLineQty(line2, "1 / 2");
            helper.assertLineSourceLocation(line2, ".../Section 2")
            helper.assertLineProduct(line3, "Compo 01");
            helper.assertLineQty(line3, "0 / 2");
            helper.assertLineSourceLocation(line3, ".../Section 3")
            helper.assertLineProduct(line4, "Compo 01");
            helper.assertLineQty(line4, "0 / 1");
            helper.assertLineSourceLocation(line4, ".../Section 4")
        }
    },

    // Scans each locations and their remaining components.
    { trigger: ".o_barcode_client_action", run: "scan LOC-01-02-00" },
    {
        trigger: ".o_barcode_line:nth-child(3) .o_highlight .o_line_source_location",
        run: "scan compo01",
    },
    { trigger: ".o_barcode_line.o_selected.o_line_completed", run: "scan shelf3" },
    {
        trigger: ".o_barcode_line:nth-child(4) .o_highlight .o_line_source_location",
        run: "scan compo01",
    },
    { trigger: ".o_barcode_line.o_selected:not(.o_line_completed)", run: "scan compo01" },
    { trigger: ".o_barcode_line.o_selected.o_line_completed", run: "scan shelf4" },
    {
        trigger: ".o_barcode_line:nth-child(5) .o_highlight .o_line_source_location",
        run: "scan compo01",
    },

    // Scans 2 more times the final product to complete the production, then validates it.
    { trigger: ".o_barcode_line.o_selected.o_line_completed", run: "scan final" },
    { trigger: ".o_barcode_client_action", run: "scan final" },
    {
        trigger: ".o_scan_message.o_scan_validate",
        run: function() { // Check all lines are here (header + 4 compos)
            const lines = helper.getLines();
            helper.assert(lines.length, 5, "The header line + 4 components lines");
            const [headerLine, line1, line2, line3, line4] = lines;
            helper.assertLineProduct(headerLine, "Final Product");
            helper.assertLineQty(headerLine, "3 / 3");
            helper.assertLineProduct(line1, "Compo 01");
            helper.assertLineSourceLocation(line1, ".../Section 1")
            helper.assertLineQty(line1, "1 / 1");
            helper.assertLineProduct(line2, "Compo 01");
            helper.assertLineQty(line2, "2 / 2");
            helper.assertLineSourceLocation(line2, ".../Section 2")
            helper.assertLineProduct(line3, "Compo 01");
            helper.assertLineQty(line3, "2 / 2");
            helper.assertLineSourceLocation(line3, ".../Section 3")
            helper.assertLineProduct(line4, "Compo 01");
            helper.assertLineQty(line4, "1 / 1");
            helper.assertLineSourceLocation(line4, ".../Section 4")
        }
    },

    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_barcode_production_scan_other_than_reserved', {test: true, steps: () => [
    {
        trigger: ".o_barcode_client_action",
        run: function() { // Check all lines are here (header + 2 compos)
            const lines = helper.getLines();
            helper.assert(lines.length, 3, "The final product line + 2 components lines");
            const [headerLine, line1, line2] = lines;
            helper.assertLineProduct(headerLine, "Final Product2");
            helper.assertLineQty(headerLine, "0 / 2");
            helper.assertLineProduct(line1, "Compo 01");
            helper.assertLineSourceLocation(line1, "WH/Stock")
            helper.assertLineQty(line1, "0 / 2");
            helper.assertLineProduct(line2, "Compo Lot");
            helper.assertLineQty(line2, "0 / 2");
            helper.assertLineSourceLocation(line2, "WH/Stock")
        }
    },
    // scan the tracked comp and the non-reserved lot in the same loc as reserved ones
    {
        trigger: ".o_scan_message.o_scan_src",
        run: "scan LOC-01-00-00",
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan compo_lot'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot_02'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot_02'
    },

    // Unfold grouped lines for tracked component
    { trigger: '.o_line_button.o_toggle_sublines' },
    {
        trigger: '.o_barcode_client_action:contains("lot_01")',
        run: function() {
            helper.assertLinesCount(3);
            helper.assertSublinesCount(2);
            const [ line1, line2 ] = helper.getSublines();
            helper.assert(line1.querySelector('.o_line_lot_name').innerText, "lot_01");
            helper.assert(line1.querySelector('.qty-done').innerText, "0");
            helper.assert(line2.querySelector('.o_line_lot_name').innerText, "lot_02");
            helper.assert(line2.querySelector('.qty-done').innerText, "2");
        }
    },
    // scan the not tracked component from a different location (shelf1) than the reserved
    {
        trigger: ".o_barcode_client_action",
        run: "scan LOC-01-01-00",
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan compo01'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan compo01'
    },
    // scan the final product + its lot name
    {
        trigger: '.o_barcode_client_action',
        run: 'scan final_lot'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan finished_lot'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan finished_lot'
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add("test_barcode_production_component_no_stock", {test: true, steps: () => [
    // Creates a new production from the Barcode App.
    { trigger: ".o_kanban_card_header:contains('Manufacturing')" },
    { trigger: ".o-kanban-button-new" },
    // Scans a product with BoM, it should add it as the final product and add a line for the component.
    {
        trigger: ".o_title.navbar-text:contains('New')",
        extra_trigger: ".o_scan_message.o_scan_product",
        run: "scan final",
    },
    /**
     * Scans the final product again, it should increment the final product qty done, but leaves component line
     * as it is, since its manual consumption (nothing reserved)
     */
    {
        trigger: ".o_scan_message.o_scan_component",
        run: "scan final",
    },
    {
        trigger: ".o_header_completed .qty-done:contains('1')",
        run: function() {
            helper.assert(helper.getLines().length, 2);
            const componentLine = helper.getLine({ barcode: "compo01" });
            helper.assertLineQty(componentLine, "2");
        }
    },
    {
        trigger: ".o_scan_message.o_scan_validate",
        run: "scan final",
    },
    {
        trigger: ".o_header_completed .qty-done:contains('2')",
        run: "scan final",
    },
    {
        trigger: ".o_header_completed .qty-done:contains('3')",
    },
    {
        trigger: ".o_validate_page",
    },
    // Confirm consumption warning
    {
        trigger: "button[name='action_confirm']",
    },
    {
        trigger: ".o_notification.border-success",
        isCheck: true,
    },
]});

registry.category("web_tour.tours").add('test_barcode_production_components_reservation_state_reserved', {test: true, steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: () => {
            helper.assertLinesCount(2);
        }
    },
]});

registry.category("web_tour.tours").add('test_barcode_production_components_reservation_state_unreserved', {test: true, steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: () => {
            helper.assertLinesCount(1);
        }
    },
]});

registry.category("web_tour.tours").add("test_barcode_production_add_scrap", {test: true, steps: () => [
    // Creates a new production from the Barcode App.
    { trigger: ".o_kanban_card_header:contains('Manufacturing')" },
    { trigger: ".o-kanban-button-new" },
    // Scans a product with BoM, it should add it as the final product and add a line for each components.
    {
        trigger: ".o_title.navbar-text:contains('New')",
        extra_trigger: ".o_scan_message.o_scan_product",
        run: "scan final",
    },
    {
        trigger: ".o_barcode_line.o_header",
        run: function() {
            const lines = helper.getLines();
            helper.assert(lines.length, 3, "The header line + 2 components lines");
            const [headerLine, componentLine1, componentLine2] = lines;
            helper.assertLineProduct(headerLine, "Final Product");
            helper.assertLineQty(headerLine, "0 / 1");
            helper.assertLineProduct(componentLine1, "Compo 01");
            helper.assertLineQty(componentLine1, "0 / 1");
            helper.assertLineProduct(componentLine2, "Compo 02");
            helper.assertLineQty(componentLine2, "0 / 1");
        }
    },
    // Add a Scrap product
    {
        trigger: ".o_barcode_client_action",
        run: "scan O-BTN.scrap",
    },
    {
        trigger: "input#product_id_0",
        run: 'text Compo 01',
    },
    { trigger: '.dropdown-item:contains("Compo 01")' },
    {
        trigger: 'button[name="action_validate"]',
        run: "click",
        // Alternatively, we may have triggered this by scanning O-BTN.VALIDATE (once focus is not on an editable input tag !)
        // However, there's still a bug such that O-BTN.VALIDATE will also validate the MO in addition to the scrap form...
    },
    // Ensure adding Compo 01 as a scrap product didn't add it as an used component
    {
        trigger: ".o_barcode_line.o_header",
        run: function() {
            const lines = helper.getLines();
            helper.assert(lines.length, 3, "The header line + 2 components lines");
            const componentLine1 = lines[1];
            helper.assertLineProduct(componentLine1, "Compo 01");
            helper.assertLineQty(componentLine1, "0 / 1");
        }
    },
    // Further assertions are done server-side as scrapped products aren't shown in barcode interface
]});

registry.category("web_tour.tours").add("test_barcode_production_add_byproduct", {test: true, steps: () => [
    // Creates a new production from the Barcode App.
    { trigger: ".o_kanban_card_header:contains('Manufacturing')" },
    { trigger: ".o-kanban-button-new" },
    //Add Bom Product
    {
        trigger: ".o_title.navbar-text:contains('New')",
        extra_trigger: ".o_scan_message.o_scan_product",
        run: "scan final",
    },

    // Add a By-Product
    { trigger: "button.o_by_products" },
    {
        trigger: ".o_barcode_client_action",
        run: "scan byproduct",
    },
    {
        trigger: ".o_barcode_line",
        run: function() {
            helper.assertLinesCount(1)
        }
    },
    // Try (unsuccesfully) to add the final product as a byproduct through scan
    {
        trigger: ".o_barcode_client_action",
        run: 'scan final'
    },
    { trigger: ".o_notification_title:contains('Product not Allowed')" },
    {
        trigger: ".o_barcode_line",
        run: function() {
            helper.assertLinesCount(1)
        }
    },
    {
        trigger: ".o_barcode_line",
        run: function() {
            const lines = helper.getLines();
            helper.assert(lines.length, 1, "The 'By Product' Line'");
            const [byProductLine] = lines;
            helper.assertLineProduct(byProductLine, "By Product");
            helper.assertLineQty(byProductLine, "1");
        }
    },
    {
        trigger: '.o_save_byproduct',
        run: 'click',
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_split_line_on_exit_for_production', {test: true, steps: () => [
    // Opens the manufacturing order and check its lines.
    { trigger: ".o_stock_barcode_main_menu", run: "scan production_split_line_on_exit" },
    {
        trigger: ".o_barcode_client_action",
        run: () => {
            helper.assertLinesCount(3);
            helper.assertLineProduct(0, "Final Product");
            helper.assertLineQty(0, "0 / 2");
            helper.assertLineProduct(1, "product1");
            helper.assertLineQty(1, "0 / 4");
            helper.assertLineProduct(2, "product2");
            helper.assertLineQty(2, "0 / 2");
        }
    },
    // Scans 1x product2 then goes back to the main menu.
    { trigger: ".o_barcode_client_action", run: "scan product2" },
    { extra_trigger: ".o_barcode_line.o_selected", trigger: "button.o_exit" },
    // Reopens the production => product2 line should be split in two.
    { trigger: ".o_stock_barcode_main_menu", run: "scan production_split_line_on_exit" },
    {
        trigger: ".o_barcode_client_action",
        run: () => {
            helper.assertLinesCount(4);
            helper.assertLineProduct(0, "Final Product");
            helper.assertLineQty(0, "0 / 2");
            helper.assertLineProduct(1, "product1");
            helper.assertLineQty(1, "0 / 4");
            helper.assertLineProduct(2, "product2");
            helper.assertLineQty(2, "0 / 1");
            helper.assertLineProduct(3, "product2");
            helper.assertLineQty(3, "1 / 1");
        }
    },
    // Scans 3x product1 then goes back again on the main menu.
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    {
        extra_trigger: ".o_barcode_line.o_selected .qty-done:contains('3')",
        trigger: "button.o_exit",
    },
    // Re-opens the MO and checks lines.
    { trigger: ".o_stock_barcode_main_menu", run: "scan production_split_line_on_exit" },
    {
        trigger: ".o_barcode_client_action",
        run: () => {
            helper.assertLinesCount(5);
            helper.assertLineProduct(0, "Final Product");
            helper.assertLineQty(0, "0 / 2");
            helper.assertLineProduct(1, "product1");
            helper.assertLineQty(1, "0 / 1");
            helper.assertLineProduct(2, "product2");
            helper.assertLineQty(2, "0 / 1");
            helper.assertLineProduct(3, "product1");
            helper.assertLineQty(3, "3 / 3");
            helper.assertLineProduct(4, "product2");
            helper.assertLineQty(4, "1 / 1");
        }
    },
]});

registry.category("web_tour.tours").add("test_barcode_production_component_different_uom", {
    test: true, steps: () => [
        // Creates a new production from the Barcode App.
        { trigger: ".o_kanban_card_header:contains('Manufacturing')" },
        { trigger: ".o-kanban-button-new" },
        // Scans a product with BoM, it should add it as the final product and add a line for the component.
        {
            trigger: ".o_barcode_client_action",
            run: "scan final",
        },
        { trigger: "button[name='produceButton']" },
        {
            trigger: ".o_header_completed",
            run: () => {
                helper.assertLineQty(1, "1 kg");
            }
        }
    ]
});

registry.category("web_tour.tours").add('test_picking_product_with_kit_and_packaging', {
    test: true, steps: () => [
        { trigger: '.btn.o_validate_page', run: 'click' }
    ]
});
