import { props, t } from "@odoo/owl";
import { TModelInput } from "@point_of_sale/app/components/inputs/t_model_input";

export class NumericInput extends TModelInput {
    static template = "point_of_sale.NumericInput";
    props = props({
        tModel: t.array(),
        class: t.string().optional(""),
        min: t.number().optional(),
    });
    parseInt(value) {
        return parseInt(value);
    }
}
