import { Component, onMounted } from "@odoo/owl";
import { ItemAddedNotification } from "@website_sale/js/cart_notification/item_added_notification/item_added_notification";
import { WarningNotification } from "../warning_notification/warning_notification";

const AUTOCLOSE_DELAY = 4000;

export class CartNotification extends Component {
    static components = { ItemAddedNotification, WarningNotification };
    static template = "website_sale.cartNotification";
    static props = {
        message: [String, { toString: Function }],
        warningMessage: {type : [String, { toString: Function }], optional: true},
        lines: {
            type: Array,
            optional: true,
            element: {
                type: Object,
                shape: {
                    id: Number,
                    linkedLineId: { type: Number, optional: true },
                    imageSrc: String,
                    quantity: Number,
                    uomName: { type: String, optional: true },
                    name: String,
                    combinationName: { type: String, optional: true },
                    description: { type: String, optional: true },
                    priceTotal: Number,
                },
            },
        },
        currencyId: {type: Number, optional: true},
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
