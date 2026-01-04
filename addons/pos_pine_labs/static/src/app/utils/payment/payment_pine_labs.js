import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { serializeDateTime } from "@web/core/l10n/dates";
import { offlineErrorHandler, handleRPCError } from "@point_of_sale/app/utils/error_handlers";
import { register_payment_method } from "@point_of_sale/app/services/pos_store";
import { ConnectionLostError, RPCError } from "@web/core/network/rpc";

const REQUEST_TIMEOUT_MS = 5000;
const CANCEL_REQUEST_TIME_LIMIT_MS = 125000;
const { DateTime } = luxon;

export class PaymentPineLabs extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.pollingTimeout = null;
        this.inactivityTimeout = null;
        this.payment_stopped = false;
    }

    sendPaymentRequest(cid) {
        super.sendPaymentRequest(cid);
        return this._processPineLabs();
    }

    pendingPineLabsPaymentLine() {
        return this.pos.getPendingPaymentLine("pine_labs");
    }

    sendPaymentCancel(order, cid) {
        super.sendPaymentCancel(order, cid);
        return this._pineLabsCancel();
    }

    _callPineLabs(data, action) {
        return this.pos.data
            .call("pos.payment.method", action, [[this.payment_method_id.id], data])
            .catch((error) => {
                const line = this.pendingPineLabsPaymentLine();
                this.pos.paymentTerminalInProgress = false;
                if (line) {
                    line.setPaymentStatus("force_done");
                }
                if (error instanceof ConnectionLostError) {
                    offlineErrorHandler(this.env, error, error);
                } else if (error instanceof RPCError) {
                    handleRPCError(error, this.env.services.dialog);
                } else {
                    throw error;
                }
            });
    }

    /**
     * Handles the response from Pine Labs for a make payment request.
     * @param {Object} response - The response received from Pine Labs.
     * @returns {Promise<Object|boolean>} - Resolves when the payment confirmation process completes.
     */
    async _makePaymentRequestHandler(response) {
        const line = this.pendingPineLabsPaymentLine();
        if (!response || response?.error) {
            line.setPaymentStatus("retry");
            this._showError(response?.error || _t("Pine Labs make payment request failed"));
            return false;
        }

        line.setPaymentStatus("waitingCard");
        line.update({ pine_labs_plutus_transaction_ref: response.plutusTransactionReferenceID });
        return await this._waitForPaymentToConfirm();
    }
    /**
     * Handles the response from Pine Labs for a payment status request.
     * @param {Object} response - The response received from Pine Labs.
     * @param {Function} callBack - The function to call for retrying the status request.
     * @param {Function} resolve - The function to resolve the promise.
     * @param {Function} reject - The function to reject the promise.
     * @returns {Promise<Object|boolean>} - Resolves with the response object on success, otherwise `false`.
     */
    _paymentStatusRequestHandler(response, callBack, resolve, reject) {
        const line = this.pos.getOrder().getSelectedPaymentline();

        if (!response || response?.error) {
            const status = response ? "retry" : "force_done";
            line.setPaymentStatus(status);
            this._showError(response?.error || _t("Pine Labs get payment status request failed"));
            if (response) {
                return resolve(false);
            }
        }
        const resultStatus = response?.status;
        if (resultStatus === "TXN UPLOADED") {
            this.pollingTimeout = setTimeout(callBack, REQUEST_TIMEOUT_MS, resolve, reject);
            return;
        } else if (
            resultStatus === "TXN APPROVED" &&
            response?.plutusTransactionReferenceID !==
                parseInt(line.pine_labs_plutus_transaction_ref)
        ) {
            response.error = _t("Reference number mismatched");
        } else if (resultStatus === "TXN APPROVED") {
            const data = response.data;
            line.update({
                payment_method_issuer_bank: data["Acquirer Name"],
                payment_method_authcode: data["ApprovalCode"],
                cardholder_name: data["Card Holder Name"],
                card_no: data["Card Number"]?.slice(-4) || "",
                card_brand: data["Card Type"],
                payment_method_payment_mode: data["PaymentMode"],
                transaction_id: data["TransactionLogId"],
                payment_date: this._getPaymentDate(
                    data["Transaction Date"],
                    data["Transaction Time"]
                ),
            });
            this._removePaymentHandler();
            return resolve(response);
        }
    }
    /**
     * Handles the response from Pine Labs for a payment cancellation request.
     * @param {Object} response - The response received from Pine Labs.
     * @returns {boolean} - Returns `true` if a notification is processed, otherwise `false`.
     */
    _paymentCancelRequestHandler(response) {
        const line = this.pendingPineLabsPaymentLine();
        if (!response || response?.error) {
            this._showError(response?.error || _t("Pine Labs payment cancellation request failed"));
            return false;
        } else if (response.notification) {
            line.setPaymentStatus("retry");
            if (this.payment_stopped) {
                this._showError(_t("Transaction failed due to inactivity"));
            } else {
                this.pos.notification.add(response.notification, {
                    type: "warning",
                    sticky: false,
                });
            }
            this._removePaymentHandler();
            return true;
        } else {
            return false;
        }
    }

    async _pineLabsCancel() {
        const paymentLine = this.pendingPineLabsPaymentLine();
        const data = {
            plutusTransactionReferenceID: paymentLine.pine_labs_plutus_transaction_ref,
            amount: paymentLine.amount * 100, // We need to provide the amount in paisa since Pine Labs processes amounts in paisa.
        };

        const response = await this._callPineLabs(data, "pine_labs_cancel_payment_request");

        return this._paymentCancelRequestHandler(response);
    }

    /**
     * This method processes order data and sends payment requests from POS to Pine Labs.
     */
    async _processPineLabs() {
        const order = this.pos.getOrder();
        const paymentLine = order.getSelectedPaymentline();
        const sequenceNumber = order.payment_ids.filter(
            (pi) => pi.payment_method_id.use_payment_terminal === "pine_labs"
        ).length;
        if (paymentLine.amount < 0) {
            this._showError(_t("Cannot process transactions with negative amount."));
            return false;
        }

        const orderId = order?.pos_reference?.replace(" ", "").replaceAll("-", "").toUpperCase();
        const referencePrefix = this.pos.config.name.replace(/\s/g, "").slice(0, 4);
        paymentLine.update({
            payment_ref_no:
                referencePrefix + "/" + orderId + "/" + crypto.randomUUID().replaceAll("-", ""),
        });

        // Assume that the Pine Labs terminal payment method is configured with INR (Indian Rupees) as the currency_id in the POS config.
        // The conversion rate between INR and paisa is set as 1 INR = 100 paisa.
        const data = {
            amount: paymentLine.amount * 100, // We need to provide the amount in paisa since Pine Labs processes amounts in paisa.
            transactionNumber: paymentLine.payment_ref_no,
            sequenceNumber: sequenceNumber, // In the case of multiple transactions for the same order, it is important to follow the correct sequence of transactions.
        };
        const response = await this._callPineLabs(data, "pine_labs_make_payment_request");
        return await this._makePaymentRequestHandler(response);
    }

    /**
     * This method waits for the payment to be confirmed by Pine Labs.
     * Also, this method uses polling to check the payment status..
     */
    async _waitForPaymentToConfirm() {
        const paymentLine = this.pos.getOrder().getSelectedPaymentline();
        if (
            !paymentLine ||
            paymentLine.payment_status == "retry" ||
            !paymentLine.pine_labs_plutus_transaction_ref
        ) {
            return false;
        }
        const data = {
            plutusTransactionReferenceID: paymentLine.pine_labs_plutus_transaction_ref,
        };
        this._stopPendingPayment().then(() => (this.payment_stopped = true));
        const pineLabsFetchPaymentStatus = async (resolve, reject) => {
            //Clear the previous timeout before setting a new one
            clearTimeout(this.pollingTimeout);

            // If the user navigates to another screen, stop the polling
            if (this.pos.router.state.current !== "PaymentScreen") {
                this._removePaymentHandler();
                return;
            }

            if (this.payment_stopped) {
                this._pineLabsCancel().then(() => {
                    paymentLine.setPaymentStatus("retry");
                    this.payment_stopped = false;
                });
                return resolve(false);
            }

            if (paymentLine.payment_status == "retry") {
                return resolve(false);
            }
            const response = await this._callPineLabs(data, "pine_labs_fetch_payment_status");
            return this._paymentStatusRequestHandler(
                response,
                pineLabsFetchPaymentStatus,
                resolve,
                reject
            );
        };
        return new Promise(pineLabsFetchPaymentStatus);
    }

    _getPaymentDate(dateString, timeString) {
        // The dateString value appears as `03122024`, while the timeString value appears as `063515`.
        const localDate = DateTime.fromFormat(`${dateString} ${timeString}`, "ddMMyyyy HHmmss");
        return serializeDateTime(localDate);
    }

    _stopPendingPayment() {
        return new Promise(
            (resolve) =>
                (this.inactivityTimeout = setTimeout(resolve, CANCEL_REQUEST_TIME_LIMIT_MS))
        );
    }

    _removePaymentHandler() {
        clearTimeout(this.pollingTimeout);
        clearTimeout(this.inactivityTimeout);
        this.payment_stopped = false;
    }

    _showError(error_msg) {
        this.env.services.dialog.add(AlertDialog, {
            title: _t("Pine Labs Error"),
            body: error_msg,
        });
    }
}

register_payment_method("pine_labs", PaymentPineLabs);
