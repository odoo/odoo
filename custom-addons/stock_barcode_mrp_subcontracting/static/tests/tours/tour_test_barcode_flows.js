/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import helper from '@stock_barcode/../tests/tours/tour_helper_stock_barcode';
import { stepUtils } from "@stock_barcode/../tests/tours/tour_step_utils";

// ----------------------------------------------------------------------------
// Tours
// ----------------------------------------------------------------------------

registry.category("web_tour.tours").add('test_receipt_classic_subcontracted_product', {test: true, steps: () => [
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
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-01-00',
    },
    // Adds a line with the "Add Product" button, then scans its destination location.
    { trigger: '.o_add_line' },
    {
        trigger: '.o_field_widget[name=product_id] input',
        run: 'text Chocolate Eclairs',
    },
    { trigger: ".ui-menu-item > a:contains('Chocolate Eclairs')" },
    {
        trigger: '[name=qty_done] input',
        run: 'text 1',
    },
    { trigger: '.o_save' },
    {
        trigger: '.o_barcode_line',
        run: 'scan LOC-01-02-00',
    },
    ...stepUtils.validateBarcodeOperation(),

]});

registry.category("web_tour.tours").add('test_receipt_tracked_subcontracted_product', {test: true, steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product_subcontracted',
    },

    {
        trigger: ".o_field_widget[name=qty_producing] input",
        position: "right",
        run: "text 1",
    },

    {
        trigger: ".modal-footer .btn[name=subcontracting_record_component]",
        content: _t('Continue'),
        position: "bottom",
    },
    {
        trigger: ".modal-footer .btn-secondary",
        extra_trigger: "button [name=product_qty]:contains(4)",
        content: _t('Discard'),
        position: "bottom",
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan O-BTN.record-components',
    },

    {
        trigger: ".o_field_widget[name=qty_producing] input",
        position: "right",
        run: "text 1",
    },

    {
        trigger: ".modal-footer .btn[name=subcontracting_record_component]",
        content: _t('Continue'),
        position: "bottom",
    },

    {
        trigger: ".modal-footer .btn-primary[name=subcontracting_record_component]",
        extra_trigger: "button [name=product_qty]:contains(3)",
        content: _t('Record production'),
        position: "bottom",
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_receipt_flexible_subcontracted_product', {test: true, steps: () => [
    {
        trigger: 'button.btn-secondary.o_mrp_subcontracting',
    },

    {
        trigger: ".o_field_widget[name=qty_producing] input",
        position: "right",
        run: "text 1",
    },
    {
        trigger: "div[name=move_line_raw_ids] td[name=quantity]",
    },

    {
        trigger: "div[name=move_line_raw_ids] [name=quantity] input",
        run: "text 2",
    },
    {
        trigger: ".modal-footer .btn-primary[name=subcontracting_record_component]",
        content: _t('Record production'),
        position: "bottom",
    },
    ...stepUtils.validateBarcodeOperation(),
]});
