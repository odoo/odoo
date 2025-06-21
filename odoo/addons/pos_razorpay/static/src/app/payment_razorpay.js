/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const REQUEST_TIMEOUT = 10000;

export class PaymentRazorpay extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.pollingTimeout = null;
        this.inactivityTimeout = null;
        this.queued = false;
        this.payment_stopped = false;
    }

    send_payment_request(cid) {
        super.send_payment_request(cid);
        return this._process_razorpay(cid);
    }

    pending_razorpay_line() {
        return this.pos.getPendingPaymentLine("razorpay");
    }

    send_payment_cancel(order, cid) {
        super.send_payment_cancel(order, cid);
        return this._razorpay_cancel();
    }

    _call_razorpay(data, action) {
        return this.env.services.orm.silent
            .call("pos.payment.method",
                action,
                [[this.payment_method.id], data]
            )
            .catch(this._handle_odoo_connection_failure.bind(this));
    }

    _handle_odoo_connection_failure(data = {}) {
        // handle timeout
        const line = this.pending_razorpay_line();
        if (line) {
            line.set_payment_status("retry");
        }
        this._showError(
            _t(
                "Could not connect to the Odoo server, please check your internet connection and try again."
            )
        );

        return Promise.reject(data); // prevent subsequent onFullFilled's from being called
    }

    /**
     * This method handles the response that comes from Razorpay
     * when we make a request for payment/cancel.
     */
    _razorpay_handle_response(response) {
        const line = this.pending_razorpay_line();
        if (response.error) {
            line.set_payment_status('force_done');
            this.payment_stopped ? this._showError(_t("Transaction failed due to inactivity")) : this._showError(response.error);
            this._removePaymentHandler(['p2pRequestId', 'referenceId']);
            return Promise.resolve(false);
        }
        line.set_payment_status("waitingCard");
        localStorage.setItem("p2pRequestId", response.p2pRequestId);
        return this._waitForPaymentConfirmation();
    }

    _razorpay_cancel() {
        const data = {'p2pRequestId': localStorage.getItem('p2pRequestId')};
        return this._call_razorpay(data, 'razorpay_cancel_payment_request').then((data) => {
            // This proficiently tackles scenarios where payment initiation is in progress and close to the completion phase
            if (data.errorMessage) {
                this._showError(data.errorMessage);
                return Promise.resolve(false);
            }
            this._razorpay_handle_response(data);
            return Promise.resolve(true);
        });
    }

    _process_razorpay(cid) {
        const order = this.pos.get_order();
        const line = order.paymentlines.find((paymentLine) => paymentLine.cid === cid);

        if (line.amount < 0) {
            this._showError(_t("Cannot process transactions with negative amount."));
            return Promise.resolve();
        }

        const orderId = order.name.replace(" ", "").replaceAll("-", "").toUpperCase();
        const referencePrefix = this.pos.config.name.replace(/\s/g, "").slice(0, 4);
        localStorage.setItem("referenceId", referencePrefix + "/" + orderId + "/" + crypto.randomUUID().replaceAll("-", ""));
        const data = {
            'amount': line.amount,
            'referenceId': localStorage.getItem('referenceId'),
        };
        return this._call_razorpay(data, 'razorpay_make_payment_request').then((data) => {
            return this._razorpay_handle_response(data);
        });
    }

    /**
     * Polling
     * This method calls and handles the razorpay status response
     * calls every 10 sec until payment is not resolved.
     */

    async _waitForPaymentConfirmation() {
        const paymentLine = this.pos.get_order()?.selected_paymentline;
        if (!paymentLine || paymentLine.payment_status == "retry") {
            return false;
        }
        const data = {'p2pRequestId': localStorage.getItem('p2pRequestId')};
        this._stop_pending_payment().then(() => this.payment_stopped = true);
        const razorpayFetchPaymentStatus = async (resolve, reject) => {

            //Clear previous timeout before setting a new one
            clearTimeout(this.pollingTimeout);

            // If the user navigates to another screen, stop the polling
            if (this.pos.mainScreen.component.name !== "PaymentScreen") {
                return;
            }

            //Within 90 seconds, inactivity will result in transaction cancellation and payment termination.
            if (this.payment_stopped) {
                this._razorpay_cancel().then(() => {
                    paymentLine.set_payment_status("force_done");
                    this.payment_stopped = false;
                });
                return resolve(false);
            }

            const response = await this._call_razorpay(data, 'razorpay_fetch_payment_status');
            if (response.error) {
                return this._razorpay_handle_response(response);
            }

            const resultCode = response?.status;

            if (resultCode === "QUEUED" && this.queued === false) {
                this._showError(_t("Payment has been queued. You may choose to wait for the payment to initiate on terminal or proceed to cancel this transaction"));
                this.queued = true;
            }
            if (resultCode === "AUTHORIZED" && response?.externalRefNumber !== localStorage.getItem('referenceId')) {
                return this._razorpay_handle_response({'error': _t("Reference number mismatched")});
            } else if (resultCode === "AUTHORIZED") {
                paymentLine.razorpay_authcode = response?.authCode;
                paymentLine.razorpay_issuer_card_no = response?.cardLastFourDigit;
                paymentLine.razorpay_issuer_bank = response?.acquirerCode;
                paymentLine.razorpay_payment_method = response?.paymentMode;
                paymentLine.card_type = response?.paymentCardType;
                paymentLine.razorpay_card_scheme = response?.paymentCardBrand;
                paymentLine.razorpay_card_owner_name = response?.nameOnCard;
                paymentLine.razorpay_reference_no = response?.externalRefNumber;
                paymentLine.razorpay_reverse_ref_no = response?.reverseReferenceNumber;
                paymentLine.transactionId = response?.txnId;
                paymentLine.payment_date = response?.createdTime;
                this._removePaymentHandler(['p2pRequestId', 'referenceId']);
                return resolve(response);
            } else {
                this.pollingTimeout = setTimeout(
                    razorpayFetchPaymentStatus,
                    REQUEST_TIMEOUT,
                    resolve,
                    reject
                );
            }
        };
        return new Promise(razorpayFetchPaymentStatus);
    }

    _stop_pending_payment() {
        return new Promise(resolve => this.inactivityTimeout = setTimeout(resolve, 90000));
    }

    _removePaymentHandler(payment_data) {
        payment_data.forEach((data) => {
            localStorage.removeItem(data);
        })
        clearTimeout(this.pollingTimeout);
        clearTimeout(this.inactivityTimeout);
        this.queued = this.payment_stopped = false;
    }

    _showError(error_msg, title) {
        this.env.services.dialog.add(AlertDialog, {
            title: title || _t("Razorpay Error"),
            body: error_msg,
        });
    }
}
