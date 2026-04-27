import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_partial_quantity_check_fail", { steps: () => [
    {
        trigger: 'footer.o_barcode_control button.o_check_quality',
        run: 'click',
    },
    {
        trigger: '.modal-footer button.btn-danger:contains("fail")',
        run: 'click',
    },
    {
        trigger: '.modal-body input.o_input[id="qty_failed_0"]',
        run: 'edit 3'
    },
    {
        trigger: '.modal-body span.o_selection_badge:contains("WH/Stock/Section 1")',
        run: 'click'
    },
    {
        trigger: 'footer.modal-footer button.btn-primary:contains("Confirm")',
        run: 'click'
    },
    {
        trigger: '.modal-footer button.btn-success:contains("pass")',
        run: 'click',
    },
    {
        trigger: 'body:not(:has(.modal))',
    },
    {
        trigger: 'header.o_barcode_header button.o_exit',
        run: 'click',
    }
]});

registry.category("web_tour.tours").add("test_operation_quality_check_barcode", {
    steps: () => [
        {
            trigger: ".o_button_operations",
            run: "click",
        },
        {
            trigger: ".o_barcode_picking_type:has(.o_kanban_record_title:contains('Receipts'))",
            run: "click",
        },
        {
            trigger: "button.o-kanban-button-new",
            run: "click",
        },
        {
            trigger: ".o_barcode_lines",
            run: "scan product1",
        },
        {
            trigger: ".fa-pencil",
            run: "click",
        },
        {
            trigger: ".o_digipad_increment",
            run: "click",
        },
        {
            trigger: ".o_save",
            run: "click",
        },
        {
            trigger: ".o_barcode_lines",
            run() {},
        },
        {
            trigger: ".o_barcode_lines",
            run: "scan product2",
        },
        {
            trigger:
                ".o_barcode_line:has(.o_barcode_line_title:contains(product2)) button.o_add_quantity",
            run: "click",
        },
        {
            trigger: ".o_validate_page",
            run: "click",
        },
        {
            trigger: ".modal-content:has(.modal-header:contains(product 1)) button[name=do_pass]",
            run: "click",
        },
        {
            trigger: ".modal-content:has(.modal-header:contains(product 2)) button[name=do_fail]",
            run: "click",
        },
        {
            trigger: ".o_notification_bar.bg-success",
            run() {},
        },
    ],
});

registry.category("web_tour.tours").add("test_operation_quality_check_delivery_barcode", {
    steps: () => [
        {
            trigger: ".o_button_operations",
            run: "click",
        },
        {
            trigger: ".o_barcode_picking_type:has(.o_kanban_record_title:contains('Delivery'))",
            run: "click",
        },
        {
            trigger: "button.o-kanban-button-new",
            run: "click",
        },
        {
            trigger: ".o_barcode_lines",
            run: "scan product1",
        },
        {
            trigger: ".fa-pencil",
            run: "click",
        },
        {
            trigger: ".o_digipad_increment",
            run: "click",
        },
        {
            trigger: ".o_save",
            run: "click",
        },
        {
            trigger: ".o_barcode_lines",
            run() {},
        },
        {
            trigger: ".o_barcode_lines",
            run: "scan product2",
        },
        {
            trigger:
                ".o_barcode_line:has(.o_barcode_line_title:contains(product2)) button.o_add_quantity",
            run: "click",
        },
        {
            trigger: ".o_validate_page",
            run: "click",
        },
        {
            trigger: ".modal-content:has(.modal-header:contains(product 1)) button[name=do_pass]",
            run: "click",
        },
        {
            trigger: ".modal-content:has(.modal-header:contains(product 2)) button[name=do_fail]",
            run: "click",
        },
        {
            trigger: ".o_notification_bar.bg-success",
            run() {},
        },
    ],
});

registry.category("web_tour.tours").add("test_quality_check_partial_reception_barcode", {
    steps: () => [
        {
            trigger: ".o_stock_barcode_main_menu",
            run: "scan WHINQCPRB",
        },
        {
            trigger: ".o_check_quality",
            run: "click",
        },
        {
            trigger:
                ".modal-content:contains(product1):has(.o_field_widget[name=nb_checks]:contains(1)) .btn-close",
            run: "click",
        },
        {
            trigger: ".o_barcode_client_action",
            run: "scan productserial1",
        },
        {
            trigger: ".o_barcode_line.o_selected:contains(productserial1)",
            run: "scan SN001",
        },
        {
            trigger: ".o_barcode_line:contains(SN001)",
        },
        // Open QC's to check that only the one related to SN001 is todo
        {
            trigger: ".o_check_quality",
            run: "click",
        },
        // Discard the dialog and check that the validation process displays the same QC
        {
            trigger: ".modal-content:has(.modal-header:contains(productserial1)) .btn-close",
            run: "click",
        },
        {
            trigger: ".o_validate_page",
            run: "click",
        },
        {
            trigger:
                ".modal-content:has(.modal-header:contains('Incomplete Transfer')) button:contains(Validate)",
            run: "click",
        },
        {
            trigger:
                ".modal-content:has(.modal-header:contains(productserial1)) button[name=do_pass]",
            run: "click",
        },
        {
            trigger: ".o_notification_bar.bg-success",
        },
    ],
});

registry.category("web_tour.tours").add("test_quality_check_packages_lots_tour", {
    steps: () => [
        // Scan product
        { trigger: '.o_barcode_client_action', run: "scan productlot1" },
        // First lot (2 units) → Pack
        { trigger: '.o_barcode_line', run: "scan lot-01" },
        { trigger: '.o_barcode_line .o_line_lot_name:contains(lot-01)' },
        { trigger: '.o_barcode_line span.qty-done:contains(1)', run: "scan lot-01" },
        { trigger: '.o_barcode_line span.qty-done:contains(2)' },
        { trigger: 'button.o_put_in_pack', run: 'click' },
        { trigger: '.o_barcode_line_summary', run: 'click' },
        // Second lot (2 units) → Pack
        { trigger: '.o_barcode_client_action', run: "scan lot-02" },
        { trigger: '.o_line_button.o_toggle_sublines', run: 'click' },
        { trigger: '.o_barcode_line .o_line_lot_name:contains(lot-02)' },
        { trigger: '.o_barcode_line span.qty-done:contains(3)', run: "scan lot-02" },
        { trigger: '.o_barcode_line span.qty-done:contains(4)' },
        { trigger: 'button.o_put_in_pack', run: 'click' },
        { trigger: '.o_barcode_line_summary', run: 'click' },
        // Validate picking → pass quality checks popup
        { trigger: '.o_check_quality', run: 'click' },
        {
            trigger: ".modal-content:has(.modal-header:contains('productlot1 - 2.0 Units - lot-01')) button[name=do_pass]",
            run: 'click',
        },
        {
            trigger: ".modal-content:has(.modal-header:contains('productlot1 - 2.0 Units - lot-02')) button[name=do_pass]",
            run: 'click',
        },
        // Final validation
        { trigger: '.o_validate_page', run: 'click' },
        { trigger: '.o_notification_bar.bg-success' },
    ],
});
