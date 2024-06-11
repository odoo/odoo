/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FloatField, floatField } from "@web/views/fields/float/float_field";

export class FloatScannableField extends FloatField {
    onBarcodeScanned() {
        this.inputRef.el.dispatchEvent(new InputEvent("input"));
    }
}
FloatScannableField.template = "barcodes.FloatScannableField";

export const floatScannableField = {
    ...floatField,
    component: FloatScannableField,
};

registry.category("fields").add("field_float_scannable", floatScannableField);
