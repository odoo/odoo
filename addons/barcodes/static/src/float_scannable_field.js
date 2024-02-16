import { registry } from "@web/core/registry";
import { FloatField, floatField } from "@web/views/fields/float/float_field";

export class FloatScannableField extends FloatField {
    static template = "barcodes.FloatScannableField";
    onBarcodeScanned() {
        this.inputRef.el.dispatchEvent(new InputEvent("input"));
    }
}

export const floatScannableField = {
    ...floatField,
    component: FloatScannableField,
};

registry.category("fields").add("field_float_scannable", floatScannableField);
