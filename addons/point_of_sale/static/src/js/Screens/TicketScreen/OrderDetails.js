/** @odoo-module */

import { LegacyComponent } from "@web/legacy/legacy_component";
import { OrderlineDetails } from "./OrderlineDetails";

/**
 * @props {models.Order} order
 */
export class OrderDetails extends LegacyComponent {
    static components = { OrderlineDetails };
    static template = "OrderDetails";

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
