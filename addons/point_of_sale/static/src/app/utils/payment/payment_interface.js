/**
 * Implement this interface to support a new payment method in the POS:
 *
 * import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
 * class MyPayment extends PaymentInterface {}
 *
 * To connect the interface to the right payment methods register it:
 *
 * import { registry } models from "@web/core/registry";
 * registry.category("pos_payment_providers").add("my_payment", MyPayment);
 *
 * my_payment is the technical name of the added selection in payment_provider
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
        this.notification = pos.notification;
        this.orm = pos.data.orm;
        this.dialog = pos.dialog;
        this.payment_method_id = payment_method_id;
        this.supports_refunds = true;
        this.auto_send_request = false;
    }

    /**
     * This getter is used for cash machines to display the amount
     * of money that has been inserted in real time. If a number is
     * returned, it will be shown as a formatted currency in the
     * payment line display.
     *
     * @returns {number | null}
     */
    get amountInserted() {
        return null;
    }

    /**
     * Called when a user clicks the "Send" button in the
     * interface, through `line.pay()`. This should initiate a payment
     * request and return a Promise that resolves once the provider
     * answered. The line is "waiting" meanwhile; an intermediate status
     * (waiting_card, waiting_scan, waiting_capture) can be set here, the
     * final one is set by handlePaymentResponse().
     *
     * For successful transactions setReceiptInfo() should be used
     * to set info that should to be printed on the receipt. You
     * should also set card_type and transaction_id on the line for
     * successful transactions.
     *
     * @param {Object} line - The payment line object
     * @returns {Promise} resolved with the provider's response, passed
     * to handlePaymentResponse(). By default a boolean that is false
     * when the payment should be retried; an interface can resolve with
     * anything else as long as its handlePaymentResponse() reads it.
     * Rejected on error, see handlePaymentResponseError().
     */
    async sendPaymentRequest(line) {}

    /**
     * Called through `line.cancelPayment()` when a user cancels a
     * payment line that's still waiting on sendPaymentRequest() to
     * complete. Should execute some
     * request to ensure the current payment request is
     * cancelled. This is not to refund payments, only to cancel
     * them. The payment line being cancelled will be deleted
     * automatically after the returned promise resolves.
     *
     * @param {Object} line - The payment line object
     * @returns {Promise} resolved with the provider's response, passed
     * to handlePaymentCancelResponse(). By default a boolean that is
     * true when the payment was cancelled.
     */
    async sendPaymentCancel(line) {}

    /**
     * Called by `line.pay()` with the response of sendPaymentRequest().
     * Sets the final status of the payment line. Override it when the
     * provider's flow differs (e.g. the payment is confirmed later by a
     * webhook). Also called when the result arrives after the request
     * promise was lost, e.g. on a refresh.
     *
     * @param {Object} line - The payment line object
     * @param {any} response - The response of sendPaymentRequest()
     * @returns {boolean} true when the order can be validated automatically
     */
    handlePaymentResponse(line, response) {
        const isPaymentSuccessful = Boolean(response);
        line.payment_status = isPaymentSuccessful ? "done" : "retry";
        return isPaymentSuccessful;
    }

    /**
     * Called by `line.pay()` when sendPaymentRequest() throws.
     *
     * @param {Object} line - The payment line object
     * @param {Error} error - The error thrown by sendPaymentRequest()
     */
    handlePaymentResponseError(line, error) {
        line.payment_status = "retry";
    }

    /**
     * Called by `line.cancelPayment()` with the response of
     * sendPaymentCancel(). A failed cancel restores the status the line
     * had before the cancel was sent.
     *
     * @param {Object} line - The payment line object
     * @param {any} response - The response of sendPaymentCancel()
     * @param {string} previousStatus - The status before the cancel was sent
     * @returns {boolean} true when the payment was cancelled
     */
    handlePaymentCancelResponse(line, response, previousStatus) {
        const isCancelSuccessful = Boolean(response);
        line.payment_status = isCancelSuccessful ? "retry" : previousStatus;
        return isCancelSuccessful;
    }

    /**
     * Called by `line.cancelPayment()` when sendPaymentCancel() throws.
     *
     * @param {Object} line - The payment line object
     * @param {Error} error - The error thrown by sendPaymentCancel()
     * @param {string} previousStatus - The status before the cancel was sent
     */
    handlePaymentCancelResponseError(line, error, previousStatus) {
        line.payment_status = previousStatus;
    }

    /**
     * Called when the user forces the payment line to done.
     *
     * @param {Object} line - The payment line object
     */
    handleForceDone(line) {
        line.payment_status = "done";
    }

    /**
     * Called when the user forces the cancellation of the payment line.
     *
     * @param {Object} line - The payment line object
     */
    handleForceCancel(line) {
        line.payment_status = "retry";
    }

    /**
     * Called when the payment screen in the POS is closed (by
     * e.g. clicking the "Back" button). Could be used to cancel in
     * progress payments.
     */
    close() {}

    /**
     * This method is a helper for the payment terminal to
     * subscribe to its corresponding bus messages in the backend,
     * enabling webhook payment confirmations.
     *
     * @param {string} channel - The message channel to subscribe to
     * @param {(message) => void} callback - The callback to run
     */
    connectWebSocket(channel, callback) {
        if (!this.pos.data.channels.some((channelInfo) => channelInfo.channel === channel)) {
            this.pos.data.connectWebSocket(channel, callback);
        }
    }

    /**
     * This wraps calls to actions on the `pos.payment.method` model.
     * It should always be used instead of calling the ORM directly, so
     * that it can be overridden in e.g. `pos_self_order`.
     *
     * @param {string} method - The action to call on `pos.payment.method`
     * @param {any[]} params - The action params to send
     */
    async callPaymentMethod(method, params) {
        return await this.env.services.orm.silent.call("pos.payment.method", method, params);
    }

    /**
     * Return true if the amount that was authorized can be modified,
     * false otherwise
     * @param {string} uuid - The id of the paymentline
     */
    canBeAdjusted(uuid) {
        return false;
    }

    /**
     * Called when the amount authorized by a payment request should
     * be adjusted to account for a new order line, it can only be called if
     * canBeAdjusted returns True
     * @param {string} uuid - The id of the paymentline
     */
    sendPaymentAdjust(uuid) {}
}
