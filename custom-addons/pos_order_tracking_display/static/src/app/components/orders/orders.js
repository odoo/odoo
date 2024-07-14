/** @odoo-module */

import { Component } from "@odoo/owl";

export class Orders extends Component {
    static template = "pos_order_tracking_display.Orders";
    static props = {
        class: { type: String, optional: true },
        categoryName: String,
        orders: { type: Array },
        ready: { type: Boolean, optional: true},
    };
    static defaultProps = {
        class: "",
        ready: false,
    };
}
