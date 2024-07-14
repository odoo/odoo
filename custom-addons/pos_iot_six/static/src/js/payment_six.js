
/** @odoo-module */
import { PaymentWorldline } from "@pos_iot/app/payment";

export class PaymentSix extends PaymentWorldline{
    get_payment_data(cid) {
        const paymentline = this.pos.get_order().get_paymentline(cid);
        const pos = this.pos;
        return {
            messageType: 'Transaction',
            transactionType: paymentline.transactionType,
            amount: Math.round(paymentline.amount*100),
            currency: pos.currency.name,
            cid: cid,
            posId: pos.pos_session.name,
            userId: pos.pos_session.user_id[0],
        };
    }

    send_payment_request(cid) {
        var paymentline = this.pos.get_order().get_paymentline(cid);
        paymentline.transactionType = 'Payment';

        return super.send_payment_request(cid);
    }
}
