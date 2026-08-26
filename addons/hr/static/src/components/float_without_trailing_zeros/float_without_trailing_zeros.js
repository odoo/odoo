import { registry } from "@web/core/registry";
import { floatField, FloatField } from "@web/views/fields/float/float_field";

const fieldRegistry = registry.category("fields");

export class FloatWithoutTrailingZeros extends FloatField {
    get formattedValue() {
        return super.formattedValue.replace(/(\.\d*?[1-9])0+$/ , "$1").replace(/\.0+$/, "");
    }
}

export const floatWithoutTrailingZeros = { ...floatField, component: FloatWithoutTrailingZeros };

fieldRegistry.add("float_without_trailing_zeros", floatWithoutTrailingZeros);
