/** @odoo-module alias=point_of_sale.PaymentScreenStatus **/

import PosComponent from 'point_of_sale.PosComponent';

class PaymentScreenStatus extends PosComponent {
    get activeOrder() {
        return this.props.activeOrder;
    }
    get changeText() {
        const change = this.env.model.getOrderChange(this.activeOrder);
        return this.env.model.formatCurrency(change);
    }
    get totalDueText() {
        const totalAmountToPay = this.env.model.getTotalAmountToPay(this.activeOrder);
        return this.env.model.formatCurrency(totalAmountToPay);
    }
    get remainingText() {
        const hasRoundedPayments = Boolean(
            this.env.model.getPayments(this.activeOrder).find((payment) => this.env.model.getShouldBeRounded(payment))
        );
        const remaining = this.env.model.getOrderDue(this.activeOrder, hasRoundedPayments);
        return this.env.model.formatCurrency(remaining);
    }
}
PaymentScreenStatus.template = 'point_of_sale.PaymentScreenStatus';

export default PaymentScreenStatus;
