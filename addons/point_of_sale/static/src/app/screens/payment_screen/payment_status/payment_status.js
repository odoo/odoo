import { Component } from "@odoo/owl";

export class PaymentScreenStatus extends Component {
    static template = "point_of_sale.PaymentScreenStatus";
    static props = {
        order: Object,
    };

    get changeText() {
        return this.env.utils.formatCurrency(this.props.order.getChange());
    }
    get remainingText() {
        const due = this.props.order.getDue();
        return this.env.utils.formatCurrency(
            this.props.order.taxTotals.order_sign * due > 0 ? due : 0
        );
    }
}
