/** @odoo-module **/

import { FormView } from "@web/views/form/form_view";
import { registry } from "@web/core/registry";

console.log('Barcode Scanner module loaded.');

FormView.include({
    on_view_load: function () {
        console.log('on_view_load called.');
        this._super.apply(this, arguments);

        const barcodeInput = this.$('input[name="scanned_barcode"]');
        if (barcodeInput.length) {
            console.log('Focusing on barcode input field.');
            barcodeInput.focus();
        } else {
            console.warn('Barcode input field is missing.');
        }
    },
});

// Register the view in the registry
registry.category("views").add("custom_odooship_decanting_process.barcode_scanner", FormView);
console.log('Barcode Scanner registered in views.');
