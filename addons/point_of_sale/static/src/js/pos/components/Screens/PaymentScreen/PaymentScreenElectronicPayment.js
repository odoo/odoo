/** @odoo-module alias=point_of_sale.PaymentScreenElectronicPayment **/

import PosComponent from 'point_of_sale.PosComponent';

/**
 * @prop {{ line: 'pos.payment' }}
 * @emits 'send-payment-request' @payload {['pos.payment', ...otherArgs]}
 * @emits 'send-payment-cancel' @payload {['pos.payment', ...otherArgs]}
 * @emits 'send-payment-reverse' @payload {['pos.payment', ...otherArgs]}
 * @emits 'send-force-done' @payload {['pos.payment', ...otherArgs]}
 */
class PaymentScreenElectronicPayment extends PosComponent {
    getPendingMessage(payment) {
        return this.env._t('Payment request pending');
    }
    getCancelledMessage(payment) {
        return this.env._t('Transaction cancelled');
    }
}
PaymentScreenElectronicPayment.template = 'point_of_sale.PaymentScreenElectronicPayment';

export default PaymentScreenElectronicPayment;
