import { props, t } from "@odoo/owl";
import { Input, inputProps } from "../input";

export class CashInput extends Input {
    static template = "point_of_sale.CashInput";
    props = props({
        ...inputProps,
        class: t.string().optional(""),
        currencySymbol: t.string().optional(""),
        currencyPosition: t.string().optional("after"),
    });
    setup() {
        super.setup(...arguments);
    }
}
