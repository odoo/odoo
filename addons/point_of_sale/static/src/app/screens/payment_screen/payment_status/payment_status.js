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
        return this.env.utils.formatCurrency(
            this.props.order.taxTotals.order_sign * this.props.order.get_due() > 0
                ? this.props.order.get_due()
                : 0
        );
    }
}
