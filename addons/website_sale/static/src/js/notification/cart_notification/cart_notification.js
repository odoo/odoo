/** @odoo-module **/

import { Component } from "@odoo/owl";
import { AddToCartNotification } from "../add_to_cart_notification/add_to_cart_notification";
import { WarningNotification } from "../warning_notification/warning_notification";

export class CartNotification extends Component {
    static components = { AddToCartNotification, WarningNotification };
    static template = "website_sale.cartNotification";
    static props = {
        message: [String, { toString: Function }],
        warning: [String, { toString: Function }],
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
}
