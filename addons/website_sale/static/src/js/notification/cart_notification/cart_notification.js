import { Component, onMounted } from "@odoo/owl";
import { AddToCartNotification } from "../add_to_cart_notification/add_to_cart_notification";
import { WarningNotification } from "../warning_notification/warning_notification";

const AUTOCLOSE_DELAY = 4000;

export class CartNotification extends Component {
    static components = { AddToCartNotification, WarningNotification };
    static template = "website_sale.cartNotification";
    static props = {
        message: [String, { toString: Function }],
        warning: {type : [String, { toString: Function }], optional: true},
        lines: {
            type: Array,
            optional: true,
            element: {
                type: Object,
                shape: {
                    id: Number,
                    linked_line_id: { type: Number, optional: true },
                    image_url: String,
                    quantity: Number,
                    uom_name: { type: String, optional: true },
                    name: String,
                    combination_name: { type: String, optional: true },
                    description: { type: String, optional: true },
                    price_total: Number,
                },
            },
        },
        currency_id: {type: Number, optional: true},
        className: String,
        close: Function,
    }

    setup() {
        onMounted(() => setTimeout(this.props.close, AUTOCLOSE_DELAY));
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
