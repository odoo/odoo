/** @odoo-module */

import { PosComponent } from "@point_of_sale/js/PosComponent";
import { float_is_zero } from "web.utils";

export class OrderSummary extends PosComponent {
    static template = "OrderSummary";

    getTotal() {
        return this.env.pos.format_currency(this.props.order.get_total_with_tax());
    }
    getTax() {
        const total = this.props.order.get_total_with_tax();
        const totalWithoutTax = this.props.order.get_total_without_tax();
        const taxAmount = total - totalWithoutTax;
        return {
            hasTax: !float_is_zero(taxAmount, this.env.pos.currency.decimal_places),
            displayAmount: this.env.pos.format_currency(taxAmount),
        };
    }
}
