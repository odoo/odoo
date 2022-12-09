/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";
import { float_is_zero } from "web.utils";

class OrderSummary extends PosComponent {
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
OrderSummary.template = "OrderSummary";

Registries.Component.add(OrderSummary);

export default OrderSummary;
