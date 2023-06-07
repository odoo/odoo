/** @odoo-module */

import { OrderlineDetails } from "@point_of_sale/app/screens/ticket_screen/order_details/orderline_details";
import { Component } from "@odoo/owl";

/**
 * @props {models.Order} order
 */
export class OrderDetails extends Component {
    static components = { OrderlineDetails };
    static template = "point_of_sale.OrderDetails";

    get order() {
        return this.props.order;
    }
    get orderlines() {
        return this.order ? this.order.orderlines : [];
    }
    get total() {
        return this.env.utils.formatCurrency(this.order ? this.order.get_total_with_tax() : 0);
    }
    get tax() {
        return this.env.utils.formatCurrency(this.order ? this.order.get_total_tax() : 0);
    }
}
