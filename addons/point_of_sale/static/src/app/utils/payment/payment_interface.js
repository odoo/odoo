/**
 * Implement this interface to support a new payment method in the POS:
 *
 * import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
 * class MyPayment extends PaymentInterface {}
 *
 * To connect the interface to the right payment methods register it:
 *
 * import { register_payment_method } models from "@point_of_sale/app/store/pos_store";
 * register_payment_method('my_payment', MyPayment);
 *
 * my_payment is the technical name of the added selection in
 * use_payment_terminal.
 *
 * If necessary new fields can be loaded on any model:
 * by overriding the loader_params of the models in the back end
 * in the `pos.session` model
 */
export class PaymentInterface {
    constructor(pos, payment_method_id) {
        this.setup(pos, payment_method_id);
    }

    setup(pos, payment_method_id) {
        this.env = pos.env;
        this.pos = pos;
        this.payment_method_id = payment_method_id;
        this.supports_reversals = false;
    }

    /**
     * This getter determines if send_payment_request
     * is called automatically upon selecting the payment method.
     * Overriding this to false allows manual input of an amount
     * before sending the request to the terminal.
     */
    get fastPayments() {
        return true;
    }

    /**
     * Called when a user clicks the "Send" button in the
     * interface. This should initiate a payment request and return a
     * Promise that resolves when the final status of the payment line
     * is set with setPaymentStatus.
     *
     * For successful transactions setReceiptInfo() should be used
     * to set info that should to be printed on the receipt. You
     * should also set card_type and transaction_id on the line for
     * successful transactions.
     *
     * @param {string} uuid - The uuid of the paymentline
     * @returns {Promise} resolved with a boolean that is false when
     * the payment should be retried. Rejected when the status of the
     * paymentline will be manually updated.
     */
    sendPaymentRequest(uuid) {}

    /**
     * Called when a user removes a payment line that's still waiting
     * on send_payment_request to complete. Should execute some
     * request to ensure the current payment request is
     * cancelled. This is not to refund payments, only to cancel
     * them. The payment line being cancelled will be deleted
     * automatically after the returned promise resolves.
     *
     * @param {} order - The order of the paymentline
     * @param {string} uuid - The id of the paymentline
     * @returns {Promise}
     */
    sendPaymentCancel(order, uuid) {}

    /**
     * This is an optional method. When implementing this make sure to
     * call enable_reversals() in the constructor of your
     * interface. This should reverse a previous payment with status
     * 'done'. The paymentline will be removed based on returned
     * Promise.
     *
     * @param {string} uuid - The id of the paymentline
     * @returns {Promise} returns true if the reversal was successful.
     */
    sendPaymentReversal(uuid) {}

    /**
     * Called when the payment screen in the POS is closed (by
     * e.g. clicking the "Back" button). Could be used to cancel in
     * progress payments.
     */
    close() {}
}
