import { Component, onMounted } from "@odoo/owl";
import { ItemAddedNotification } from "@website_sale/js/cart_notification/item_added_notification/item_added_notification";
import { WarningNotification } from "../warning_notification/warning_notification";

const AUTOCLOSE_DELAY = 4000;

export class CartNotification extends Component {
    static components = { ItemAddedNotification, WarningNotification };
    static template = "website_sale.CartNotification";
    static props = {
        message: [String, { toString: Function }],
        warning_message: {type : [String, { toString: Function }], optional: true},
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
                    combination_name: { type: String, optional: true },
                    name: String,
                    description: { type: String, optional: true },
                    price_total: Number,
                },
            },
        },
        currency_id: {type: Number, optional: true},
        className: String,
        close: Function,
        refresh: Function,
        freeze: Function,
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
