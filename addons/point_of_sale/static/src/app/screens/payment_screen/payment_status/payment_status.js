import { Component } from "@odoo/owl";

export class PaymentScreenStatus extends Component {
    static template = "point_of_sale.PaymentScreenStatus";
    static props = {
        order: Object,
    };

    get changeText() {
        return this.env.utils.formatCurrency(this.props.order.get_change());
    }
    get remainingText() {
        const { order_has_zero_remaining, order_remaining, order_sign } =
            this.props.order.taxTotals;
        if (order_has_zero_remaining) {
            return this.env.utils.formatCurrency(0);
        }
        return this.env.utils.formatCurrency(order_sign * order_remaining);
    }
}
