import { props, types } from "@odoo/owl";
import { Input } from "../input";

export class CashInput extends Input {
    static template = "point_of_sale.CashInput";
    setup() {
        super.setup(...arguments);
        this.cashInputProps = props(
            {
                "class?": types.string(),
                "currencySymbol?": types.string(),
                "currencyPosition?": types.string(),
            },
            {
                class: "",
                currencySymbol: "",
                currencyPosition: "after",
            }
        );
    }
}
