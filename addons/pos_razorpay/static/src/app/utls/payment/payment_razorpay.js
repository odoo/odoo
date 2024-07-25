import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { serializeDateTime } from "@web/core/l10n/dates";
import { register_payment_method } from "@point_of_sale/app/services/pos_store";

const REQUEST_TIMEOUT = 10000;
const { DateTime } = luxon;

export class PaymentRazorpay extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.pollingTimeout = null;
        this.inactivityTimeout = null;
        this.queued = false;
        this.payment_stopped = false;
    }

    sendPaymentRequest(cid) {
        super.sendPaymentRequest(cid);
        return this._processRazorpay(cid);
    }

    pendingRazorpayline() {
        return this.pos.getPendingPaymentLine("razorpay");
    }

    sendPaymentCancel(order, cid) {
        super.sendPaymentCancel(order, cid);
        return this._razorpayCancel();
    }

    _callRazorpay(data, action) {
        return this.env.services.orm.silent
            .call("pos.payment.method", action, [[this.payment_method_id.id], data])
            .catch(this._handleOdooConnectionFailure.bind(this));
    }

    _handleOdooConnectionFailure(data = {}) {
        // handle timeout
        const line = this.pendingRazorpayline();
        if (line) {
            line.setPaymentStatus("retry");
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
    _razorpayHandleResponse(response) {
        const line = this.pendingRazorpayline();
        if (response.error) {
            line.setPaymentStatus("force_done");
            this.payment_stopped
                ? this._showError(_t("Transaction failed due to inactivity"))
                : this._showError(response.error);
            if (response.payment_messageCode === "P2P_DEVICE_CANCELED") {
                line.setPaymentStatus("retry");
            }
            this._removePaymentHandler(["p2pRequestId", "referenceId"]);
            return Promise.resolve(false);
        }
        line.setPaymentStatus("waitingCard");
        localStorage.setItem("p2pRequestId", response.p2pRequestId);
        return this._waitForPaymentConfirmation();
    }

    _razorpayCancel() {
        const data = { p2pRequestId: localStorage.getItem("p2pRequestId") };
        return this._callRazorpay(data, "razorpay_cancel_payment_request").then((data) => {
            // This proficiently tackles scenarios where payment initiation is in progress and close to the completion phase
            if (data.errorMessage) {
                this._showError(data.errorMessage);
                return Promise.resolve(false);
            }
            this._razorpayHandleResponse(data);
            return Promise.resolve(true);
        });
    }

    _razorpayHandleRefundResponse(response) {
        const paymentLine = this.pendingRazorpayline();
        if (response?.error) {
            paymentLine.setPaymentStatus("retry");
            this._showError(response.error);
            this._removePaymentHandler(["referenceId"]);
            return false;
        }
        const resultCode = response?.status;
        if (
            resultCode === "REFUNDED" &&
            response?.externalRefNumber !== localStorage.getItem("referenceId")
        ) {
            return this._razorpayHandleRefundResponse({
                error: _t("Reference number mismatched"),
            });
        } else if (resultCode === "REFUNDED" || resultCode === "VOIDED") {
            this._updatePaymentLine(paymentLine, response);
            paymentLine.payment_date = this._getPaymentDate(response?.postingDate - 19800000);
            paymentLine.setPaymentStatus("done");
            this._removePaymentHandler(["referenceId"]);
        }
        return Promise.resolve(true);
    }

    _updatePaymentLine(paymentLine, response) {
        paymentLine.update({
            payment_method_authcode: response?.authCode,
            card_no: response?.cardLastFourDigit || "",
            payment_method_issuer_bank: response?.acquirerCode,
            payment_method_payment_mode: response?.paymentMode,
            card_type: response?.paymentCardType,
            card_brand: response?.paymentCardBrand || "",
            cardholder_name: response?.nameOnCard.replace("/", ""),
            razorpay_reverse_ref_no: response?.reverseReferenceNumber,
            transaction_id: response?.txnId,
            payment_ref_no: response?.externalRefNumber,
        });
    }

    async _processRazorpay(cid) {
        const order = this.pos.getOrder();
        const line = order.getSelectedPaymentline();

        if (line.amount < 0 && !order._isRefundOrder()) {
            this._showError(_t("Cannot process transactions with negative amount."));
            return Promise.resolve();
        }

        const orderId = order.pos_reference.replace(" ", "").replaceAll("-", "").toUpperCase();
        const referencePrefix = this.pos.config.name.replace(/\s/g, "").slice(0, 4);
        localStorage.setItem(
            "referenceId",
            referencePrefix + "/" + orderId + "/" + crypto.randomUUID().replaceAll("-", "")
        );
        if (order._isRefundOrder()) {
            line.setPaymentStatus("waitingCard");
            const data = {
                amount: Math.abs(line.amount),
                externalRefNumber: localStorage.getItem("referenceId"),
                transaction_id: line?.transaction_id,
            };
            const response = await this._checkPaymentStatus(line);
            if (response?.settlementStatus === "SETTLED") {
                data.refund_type = "refund";
            } else {
                const refundedOrder = order.lines[0].refunded_orderline_id.order_id;
                const refundedPaymentLine = refundedOrder.payment_ids.find(
                    (pi) => pi.transaction_id === line.transaction_id
                );
                if (Math.abs(line.amount) < refundedPaymentLine.amount) {
                    try {
                        const userConfirmed = await this._confirmVoidPayment();
                        if (!userConfirmed) {
                            return false;
                        }
                    } catch (error) {
                        console.error(error);
                        return false;
                    }
                }
                data.refund_type = "void";
            }
            response?.settlementStatus === "SETTLED"
                ? (data.refund_type = "refund")
                : (data.refund_type = "void");
            return this._callRazorpay(data, "razorpay_make_refund_request").then((data) =>
                this._razorpayHandleRefundResponse(data)
            );
        } else {
            const data = {
                amount: line.amount,
                referenceId: localStorage.getItem("referenceId"),
            };
            return this._callRazorpay(data, "razorpay_make_payment_request").then((data) =>
                this._razorpayHandleResponse(data)
            );
        }
    }

    /**
     * This method verifies the card payment before processing.
     * If the payment is settled, we will proceed with the refund; otherwise, we will void it.
     */
    async _checkPaymentStatus(line) {
        const data = { p2pRequestId: line?.razorpay_p2p_request_id };
        const response = await this._callRazorpay(data, "razorpay_fetch_payment_status");
        return response;
    }

    /**
     * Polling
     * This method calls and handles the razorpay status response
     * calls every 10 sec until payment is not resolved.
     */

    async _waitForPaymentConfirmation() {
        const paymentLine = this.pos.getOrder().getSelectedPaymentline();
        if (!paymentLine || paymentLine.payment_status == "retry") {
            return false;
        }
        const data = { p2pRequestId: localStorage.getItem("p2pRequestId") };
        this._stopPendingPayment().then(() => (this.payment_stopped = true));
        const razorpayFetchPaymentStatus = async (resolve, reject) => {
            //Clear previous timeout before setting a new one
            clearTimeout(this.pollingTimeout);

            //Within 90 seconds, inactivity will result in transaction cancellation and payment termination.
            if (this.payment_stopped) {
                this._razorpayCancel().then(() => {
                    paymentLine.setPaymentStatus("retry");
                    this.payment_stopped = false;
                });
                return resolve(false);
            }

            const response = await this._callRazorpay(data, "razorpay_fetch_payment_status");
            if (response.error) {
                return this._razorpayHandleResponse(response);
            }

            const resultCode = response?.status;

            if (resultCode === "QUEUED" && this.queued === false) {
                this._showError(
                    _t(
                        "Payment has been queued. You may choose to wait for the payment to initiate on terminal or proceed to cancel this transaction"
                    )
                );
                this.queued = true;
            }
            if (
                resultCode === "AUTHORIZED" &&
                response?.externalRefNumber !== localStorage.getItem("referenceId")
            ) {
                return this._razorpayHandleResponse({ error: _t("Reference number mismatched") });
            } else if (resultCode === "AUTHORIZED") {
                this._updatePaymentLine(paymentLine, response);
                paymentLine.razorpay_p2p_request_id = response?.p2pRequestId;
                // `createdTime` is provided in milliseconds in local GMT+5.5 timezone.
                // Thus, we need to subtract 19800000 to get the correct time in milliseconds.
                paymentLine.payment_date = this._getPaymentDate(response?.createdTime - 19800000);
                this._removePaymentHandler(["p2pRequestId", "referenceId"]);
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

    _getPaymentDate(timeMillis) {
        const utcDate = timeMillis
            ? DateTime.fromMillis(timeMillis, { zone: "utc" })
            : DateTime.now();
        return serializeDateTime(utcDate);
    }

    _stopPendingPayment() {
        return new Promise((resolve) => (this.inactivityTimeout = setTimeout(resolve, 90000)));
    }

    _removePaymentHandler(payment_data) {
        payment_data.forEach((data) => {
            localStorage.removeItem(data);
        });
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

    async _confirmVoidPayment() {
        return new Promise((resolve, reject) => {
            this.env.services.dialog.add(ConfirmationDialog, {
                title: _t("Void Payment Confirmation"),
                body: _t(
                    "Your transaction isn't settled yet, and the refund is less than the amount paid.\n" +
                        "The full amount will be cancelled, do you want to proceed?"
                ),
                confirmLabel: _t("Void Transaction"),
                cancelLabel: _t("Cancel"),
                confirm: () => resolve(true),
                cancel: () => reject(false),
            });
        });
    }
}

register_payment_method("razorpay", PaymentRazorpay);
