/** @odoo-module */

import { OrderlineDetails } from "./OrderlineDetails";
import { Component } from "@odoo/owl";

/**
 * @props {models.Order} order
 */
export class OrderDetails extends Component {
    static components = { OrderlineDetails };
    static template = "OrderDetails";
    static props = {
        onClickOrderline: { type: Function, optional: true },
        onClickRefundOrderUid: { type: Function, optional: true },
        order: { type: "object", optional: true },
        selectedOrderlineId: { type: Number, optional: true },
        highlightHeaderNote: { type: Boolean, optional: true },
    };

    get order() {
        return this.props.order;
    }
    get orderlines() {
        return this.order ? this.order.orderlines : [];
    }
    get total() {
        return this.env.pos.format_currency(this.order ? this.order.get_total_with_tax() : 0);
    }
    get tax() {
        return this.env.pos.format_currency(this.order ? this.order.get_total_tax() : 0);
    }
}
