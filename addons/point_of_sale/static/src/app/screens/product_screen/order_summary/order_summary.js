/** @odoo-module */

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { floatIsZero } from "@web/core/utils/numbers";

export class OrderSummary extends Component {
    static template = "point_of_sale.OrderSummary";

    setup() {
        this.pos = usePos();
    }
    getTotal() {
        return this.env.utils.formatCurrency(this.props.order.get_total_with_tax());
    }
    getTax() {
        const total = this.props.order.get_total_with_tax();
        const totalWithoutTax = this.props.order.get_total_without_tax();
        const taxAmount = total - totalWithoutTax;
        return {
            hasTax: !floatIsZero(taxAmount, this.pos.currency.decimal_places),
            displayAmount: this.env.utils.formatCurrency(taxAmount),
        };
    }
}
