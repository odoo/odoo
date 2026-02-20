import { FloatField, floatField } from "@web/views/fields/float/float_field";
import {registry} from "@web/core/registry";

class FloatFieldWithOperator extends FloatField {
    static defaultProps = FloatField.defaultProps;
    static template = "account.FloatFieldWithOperator"

    get digitsCount() {
        const [, decPart = ""] = this.value.toString().split(".");
        return decPart.length;
    }
}

export const floatFieldWithOperator = {
    ...floatField,
    component: FloatFieldWithOperator,
};

registry.category("fields").add("float_field_with_operator", floatFieldWithOperator);
