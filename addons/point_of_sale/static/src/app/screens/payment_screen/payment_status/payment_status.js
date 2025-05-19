import { Component } from "@odoo/owl";
import { PriceFormatter } from "@point_of_sale/app/components/price_formatter/price_formatter";

export class PaymentScreenStatus extends Component {
    static template = "point_of_sale.PaymentScreenStatus";
    static props = {
        order: Object,
    };
    static components = { PriceFormatter };

    get changeText() {
        return this.env.utils.formatCurrency(this.props.order.getChange());
    }
    get remainingText() {
        const { order_remaining, order_sign } = this.props.order.taxTotals;
        if (this.props.order.orderHasZeroRemaining) {
            return this.env.utils.formatCurrency(0);
        }
        return this.env.utils.formatCurrency(order_sign * order_remaining);
    }
}
