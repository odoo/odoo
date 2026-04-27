/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import * as helper from '@stock_barcode/../tests/tours/tour_helper_stock_barcode';
import { stepUtils } from "@stock_barcode/../tests/tours/tour_step_utils";

// ----------------------------------------------------------------------------
// Tours
// ----------------------------------------------------------------------------

registry.category("web_tour.tours").add('test_receipt_classic_subcontracted_product', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            const button = document.querySelector('button.o_mrp_subcontracting');
            helper.assert(button, null, "Button record component shouldn't be in the DOM");
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product_subcontracted',
    },

    {
        trigger: '.o_barcode_line.o_selected',
        run: 'scan LOC-01-01-00',
    },
    { trigger: '.o_barcode_line:nth-child(2)' },
    // Adds a line with the "Add Product" button, then scans its destination location.
    {
        trigger: '.o_add_line',
        run: "click",
    },
    {
        trigger: '.o_field_widget[name=product_id] input',
        run: "edit Chocolate Eclairs",
    },
    {
        trigger: ".ui-menu-item > a:contains('Chocolate Eclairs')",
        run: "click",
    },
    {
        trigger: '[name=qty_done] input',
        run: "edit 1",
    },
    {
        trigger: '.o_save',
        run: "click",
    },
    {
        trigger: '.o_barcode_line',
        run: 'scan LOC-01-02-00',
    },
    ...stepUtils.validateBarcodeOperation(".o_barcode_line:nth-child(2):not(.o_selected)"),

]});

registry.category("web_tour.tours").add('test_receipt_tracked_subcontracted_product', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product_subcontracted',
    },

    {
        trigger: ".o_field_widget[name=qty_producing] input",
        tooltipPosition: "right",
        run: "edit 1 && click body",
    },

    {
        trigger: ".modal-footer .btn[name=subcontracting_record_component]",
        content: _t('Continue'),
        tooltipPosition: "bottom",
        run: "click",
    },
    {
        trigger: "button [name=product_qty]:contains(4)",
    },
    {
        trigger: ".modal-footer .btn-secondary",
        content: _t('Discard'),
        tooltipPosition: "bottom",
        run: "click",
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan OBTRECO',
    },

    {
        trigger: ".o_field_widget[name=qty_producing] input",
        tooltipPosition: "right",
        run: "edit 1 && click body",
    },

    {
        trigger: ".modal-footer .btn[name=subcontracting_record_component]",
        content: _t('Continue'),
        tooltipPosition: "bottom",
        run: "click",
    },
    {
        trigger: "button [name=product_qty]:contains(3)",
    },
    {
        trigger: ".modal-footer .btn-primary[name=subcontracting_record_component]",
        content: _t('Record production'),
        tooltipPosition: "bottom",
        run: "click",
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add("test_receipt_flexible_subcontracted_product", {
    steps: () => [
        {
            trigger: "button.btn-secondary.o_mrp_subcontracting",
            run: "click",
        },

        {
            trigger: ".modal .o_field_widget[name=qty_producing] input",
            tooltipPosition: "right",
            run: "edit 1 && click .modal-body",
        },
        {
            trigger: ".modal div[name=move_line_raw_ids] td[name=quantity]",
            run: "click",
        },

        {
            trigger: ".modal div[name=move_line_raw_ids] [name=quantity] input",
            run: "edit 2",
        },
        {
            trigger: ".modal .modal-footer .btn-primary[name=subcontracting_record_component]",
            content: _t("Record production"),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal))",
        },
        ...stepUtils.validateBarcodeOperation(),
    ],
});

registry.category("web_tour.tours").add('test_receipt_subcontract_bom_product_manual_add_src_location', { steps: () => [
        { trigger: 'button.o_add_remaining_quantity', run: 'click' },
        { trigger: 'button.o_add_line', run: 'click' },
        {
            trigger: 'div[name=product_id] input',
            run: 'edit Chocolate Eclairs',
        },
        {
            trigger: '.dropdown-item:not(:has(.o_m2o_dropdown_option_create)):contains(\'Chocolate Eclairs\')',
            run: 'click',
        },
        { trigger: 'button.o_save', run: 'click' },
        { trigger: 'button.o_validate_page', run: 'click' },
]});

registry.category("web_tour.tours").add('test_partial_subcontract_receipt_and_backorder', {
    steps: () => [
        {
            content: 'Mark the subcontracted product for delivery',
            trigger: 'div.o_barcode_line:contains("Chocolate Eclairs") button.o_add_remaining_quantity',
            run: 'click',
        },
        {
            content: 'Await qty_done update',
            trigger: 'div.o_barcode_line:contains("Chocolate Eclairs") .qty-done:contains("5")',
            run: () => {},
        },
        {
            content: 'Validate reception',
            trigger: 'footer.o_barcode_control button.o_validate_page',
            run: 'click',
        },
        {
            content: 'Await backorder window popup',
            trigger: 'div.o_barcode_backorder_dialog',
            run: () => {},
        },
        {
            content: 'Validate the incomplete transfer',
            trigger: 'div.o_barcode_backorder_dialog button:contains("Validate")',
            run: 'click',
        },
        {
            content: 'Await backorder notification',
            trigger: 'div.o_notification_body:contains("Following backorder was created")',
            run: () => {},
        },
]});
