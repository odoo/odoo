import { monetaryField, MonetaryField } from "@web/views/fields/monetary/monetary_field";
import { registry } from "@web/core/registry";
import { floatIsZero } from "@web/core/utils/numbers";

export class MonetaryFieldNoZero extends MonetaryField {
    static props = {
        ...MonetaryField.props,
    };

    /** Override **/
    get value() {
        const originalValue = super.value;
        const decimals = this.currencyDigits ? this.currencyDigits[1] : 2;
        return floatIsZero(originalValue, decimals) ? false : originalValue;
    }
}

export const monetaryFieldNoZero = {
    ...monetaryField,
    component: MonetaryFieldNoZero,
};

registry.category("fields").add("monetary_no_zero", monetaryFieldNoZero);
