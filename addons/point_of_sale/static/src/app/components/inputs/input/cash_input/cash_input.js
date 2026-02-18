import { Input } from "../input";

export class CashInput extends Input {
    static template = "point_of_sale.CashInput";
    static props = {
        ...super.props,
        class: { type: String, optional: true },
        currencySymbol: { type: String, optional: true },
        currencyPosition: { type: String, optional: true },
    };
    static defaultProps = {
        ...super.defaultProps,
        class: "",
        currencySymbol: "",
        currencyPosition: "after",
    };
    setup() {
        super.setup(...arguments);
    }
}
