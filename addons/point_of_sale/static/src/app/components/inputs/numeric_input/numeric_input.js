import { props, types } from "@odoo/owl";
import { TModelInput } from "@point_of_sale/app/components/inputs/t_model_input";

export class NumericInput extends TModelInput {
    static template = "point_of_sale.NumericInput";
    setup() {
        this.numericInputProps = props(
            {
                "class?": types.string(),
                "min?": types.number(),
            },
            {
                class: "",
            }
        );
    }
    parseInt(value) {
        return parseInt(value);
    }
}
