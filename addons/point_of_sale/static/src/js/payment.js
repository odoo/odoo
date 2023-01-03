/** @odoo-module */

import core from "web.core";

/**
 * Implement this interface to support a new payment method in the POS:
 *
 import var PaymentInterface from "@point_of_sale/js/payment";
 * var MyPayment = PaymentInterface.extend({
 *     ...
 * })
 *
 * To connect the interface to the right payment methods register it:
 *
 * import { register_payment_method } models from "@point_of_sale/js/models";
 * register_payment_method('my_payment', MyPayment);
 *
 * my_payment is the technical name of the added selection in
 * use_payment_terminal.
 *
 * If necessary new fields can be loaded on any model:
 * by overriding the loader_params of the models in the back end
 * in the `pos.session` model
 */
var PaymentInterface = core.Class.extend({
    init: function (pos, payment_method) {
        this.pos = pos;
        this.payment_method = payment_method;
        this.supports_reversals = false;
    },

    /**
     * Call this function to enable UI elements that allow a user to
     * reverse a payment. This requires that you implement
     * send_payment_reversal.
     */
    enable_reversals: function () {
        this.supports_reversals = true;
    },

    /**
     * Called when a user clicks the "Send" button in the
     * interface. This should initiate a payment request and return a
     * Promise that resolves when the final status of the payment line
     * is set with set_payment_status.
     *
     * For successful transactions set_receipt_info() should be used
     * to set info that should to be printed on the receipt. You
     * should also set card_type and transaction_id on the line for
     * successful transactions.
     *
     * @param {string} cid - The id of the paymentline
     * @returns {Promise} resolved with a boolean that is false when
     * the payment should be retried. Rejected when the status of the
     * paymentline will be manually updated.
     */
    send_payment_request: function (cid) {},

    /**
     * Called when a user removes a payment line that's still waiting
     * on send_payment_request to complete. Should execute some
     * request to ensure the current payment request is
     * cancelled. This is not to refund payments, only to cancel
     * them. The payment line being cancelled will be deleted
     * automatically after the returned promise resolves.
     *
     * @param {} order - The order of the paymentline
     * @param {string} cid - The id of the paymentline
     * @returns {Promise}
     */
    send_payment_cancel: function (order, cid) {},

    /**
     * This is an optional method. When implementing this make sure to
     * call enable_reversals() in the constructor of your
     * interface. This should reverse a previous payment with status
     * 'done'. The paymentline will be removed based on returned
     * Promise.
     *
     * @param {string} cid - The id of the paymentline
     * @returns {Promise} returns true if the reversal was successful.
     */
    send_payment_reversal: function (cid) {},

    /**
     * Called when the payment screen in the POS is closed (by
     * e.g. clicking the "Back" button). Could be used to cancel in
     * progress payments.
     */
    close: function () {},
});

export default PaymentInterface;
