import { Component } from "@odoo/owl";

export class PriceFormatter extends Component {
    static template = "point_of_sale.PriceFormatter";
    static props = {
        price: { type: String },
    };

    get priceParts() {
        const match = this.props.price.match(/([\D]*)(\d[\d,]*)(\.(\d+))?([\D]*)/);
        if (!match) {
            return { prefix: "", amount: this.props.price, decimal: "", suffix: "" };
        }
        const [, prefix, amount, , decimal = "", suffix] = match;
        return {
            prefix: prefix.trim(),
            amount: amount + (decimal ? "." : ""),
            decimal: decimal,
            suffix: suffix.trim(),
        };
    }
}
