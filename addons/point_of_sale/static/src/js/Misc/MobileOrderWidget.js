/** @odoo-module */

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/pos_hook";

export class MobileOrderWidget extends Component {
    static template = "MobileOrderWidget";

    setup() {
        super.setup(...arguments);
        this.pos = usePos();
    }
    get order() {
        return this.pos.globalState.get_order();
    }
    get total() {
        const _total = this.order ? this.order.get_total_with_tax() : 0;
        return this.env.utils.formatCurrency(_total);
    }
    get items_number() {
        return this.order
            ? this.order.orderlines.reduce((items_number, line) => items_number + line.quantity, 0)
            : 0;
    }
    clickPay() {
        const order = this.pos.globalState.get_order();

        if (order.orderlines.length) {
            order.pay();
        }
    }
}
