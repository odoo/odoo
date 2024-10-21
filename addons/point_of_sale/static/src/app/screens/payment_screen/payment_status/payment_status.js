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
        return this.env.utils.formatCurrency(
            this.props.order.getDue() > 0 ? this.props.order.getDue() : 0
        );
    }
}
