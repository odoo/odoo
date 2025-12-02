import { FloatField, floatField } from "@web/views/fields/float/float_field";
import { roundPrecision } from "@web/core/utils/numbers";
import {registry} from "@web/core/registry";

export class AccountTaxRepartitionLineFactorPercent extends FloatField {
    static defaultProps = {
        ...FloatField.defaultProps,
        digits: [16, 12],
    };

    /*
     * @override
     * We don't want to display all amounts with 12 digits behind so we remove the trailing 0
     * as much as possible.
     */
    get formattedValue() {
        const value = super.formattedValue;
        const trailingNumbersMatch = value.match(/(\d+)$/);
        if (!trailingNumbersMatch) {
            return value;
        }
        const trailingZeroMatch = trailingNumbersMatch[1].match(/(0+)$/);
        if (!trailingZeroMatch) {
            return value;
        }
        const nbTrailingZeroToRemove = Math.min(trailingZeroMatch[1].length, trailingNumbersMatch[1].length - 2);
        return value.substring(0, value.length - nbTrailingZeroToRemove);
    }

    /*
     * @override
     * Prevent the users of showing a rounding at 12 digits on the screen but
     * getting an unrounded value after typing "= 2/3" on the field when saving.
     */
    parse(value) {
        const parsedValue = super.parse(value);
        try {
            Number(parsedValue);
        } catch {
            return parsedValue;
        }
        const precisionRounding = Number(`1e-${this.props.digits[1]}`);
        return roundPrecision(parsedValue, precisionRounding);
    }
}


export const accountTaxRepartitionLineFactorPercent = {
    ...floatField,
    component: AccountTaxRepartitionLineFactorPercent,
};


registry.category("fields").add("account_tax_repartition_line_factor_percent", accountTaxRepartitionLineFactorPercent);
