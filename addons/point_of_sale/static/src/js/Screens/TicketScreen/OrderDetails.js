/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

/**
 * @props {models.Order} order
 */
class OrderDetails extends PosComponent {
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
OrderDetails.template = "OrderDetails";

Registries.Component.add(OrderDetails);

export default OrderDetails;
