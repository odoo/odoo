import { Component, t, useProps } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";

export class BadgeExtraPrice extends Component {
    static template = "sale.BadgeExtraPrice";
    props = useProps({
        price: t.number(),
        currencyId: t.number(),
    });

    /**
     * Return the price, in the format of the given currency.
     *
     * @return {String} - The price, in the format of the given currency.
     */
    getFormattedPrice() {
        return formatCurrency( Math.abs(this.props.price), this.props.currencyId);
    }
}
