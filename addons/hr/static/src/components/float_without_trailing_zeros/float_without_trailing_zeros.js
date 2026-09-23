/** @odoo-module native */
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { escapeRegExp } from "@web/core/utils/format/strings";
import { FloatField, floatField } from "@web/fields/basic/float/float_field";

const fieldRegistry = registry.category("fields");

class FloatWithoutTrailingZeros extends FloatField {
    get formattedValue() {
        // `formatFloat` joins the two halves with the active language's
        // decimal separator, not a literal dot, so the patterns have to be
        // built from it: hardcoding "." made this a silent no-op in every
        // comma-decimal locale.
        const decimalPoint = escapeRegExp(localization.decimalPoint);
        return super.formattedValue
            .replace(new RegExp(`(${decimalPoint}\\d*?[1-9])0+$`), "$1")
            .replace(new RegExp(`${decimalPoint}0+$`), "");
    }
}

const floatWithoutTrailingZeros = {
    ...floatField,
    component: FloatWithoutTrailingZeros,
};

fieldRegistry.add("float_without_trailing_zeros", floatWithoutTrailingZeros);
