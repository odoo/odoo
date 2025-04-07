import { registry } from "@web/core/registry";
import { FloatField, floatField } from "@web/views/fields/float/float_field";

export class RoundedFloatField extends FloatField {
    setup() {
        super.setup();
        const { data, fields } = this.props.record;
        if (!!fields.rounding) {
            this.props.digits = [0, Math.ceil(-Math.log10(data[fields.rounding.name]))];
        }
    }
}

export const roundedFloatField = {
    ...floatField,
    component: RoundedFloatField,
};

registry.category("fields").add("rounded_float", roundedFloatField);
