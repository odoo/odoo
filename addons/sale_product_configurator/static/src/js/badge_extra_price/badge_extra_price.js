/** @odoo-module **/

import { Component } from "@odoo/owl";
import { formatMonetary } from "@web/views/fields/formatters";

export class BadgeExtraPrice extends Component {
    static template = "product.badge_extra_price";
    static props = {
        price: Number,
        currencyId: Number,
    };

    /**
     * Return the price, in the format of the given currency.
     *
     * @return {String} - The price, in the format of the given currency.
     */
    getFormattedPrice() {
        return formatMonetary( Math.abs(this.props.price), {currencyId: this.props.currencyId});
    }
}
