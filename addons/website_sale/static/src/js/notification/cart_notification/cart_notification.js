/** @odoo-module **/

import { Component } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";

export class CartNotification extends Component {
    static template = "website_sale.cartNotification";
    static props = {
        message: [String, { toString: Function }],
        lines: {
            type: Array,
            element: {
                type: Object,
                shape: {
                    id: Number,
                    image_url: String,
                    quantity: Number,
                    name: String,
                    description: { type: String, optional: true },
                    line_price_total: Number,
                },
            },
        },
        currency_id: Number,
        className: String,
        close: Function,
    }

    /**
     * Get the top position (in px) of the notification based on the navbar height.
     *
     * This prevents the notification from being shown in front of the navbar.
     */
    get positionOffset() {
        return (document.querySelector('header.o_top_fixed_element')?.offsetHeight || 0) + 'px';
    }

    /**
     * Return the price, in the format of the sale order currency.
     *
     * @param {Object} line - The line element for which to return the formatted price.
     * @return {String} - The price, in the format of the sale order currency.
     */
    getFormattedPrice(line) {
        return formatCurrency(line.line_price_total, this.props.currency_id);
    }

    /**
     * Return the product summary based on the line information.
     *
     * The product summary is computed based on the line quantity and name, separated by the symbol
     * 'x' (e.g.: 1 x Chair Floor Protection).
     *
     * @param {Object} line - The line element for which to return the product summary.
     * @return {String} - The product summary.
     */
    getProductSummary(line) {
        return line.quantity + " x " + line.name;
    }
}
