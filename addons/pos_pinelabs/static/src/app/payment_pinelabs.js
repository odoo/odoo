import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { serializeDateTime } from "@web/core/l10n/dates";

const REQUEST_TIMEOUT = 10000;
const CANCEL_REQUEST_TIME_LIMIT = 125000;
const { DateTime } = luxon;

export class PaymentPinelabs extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.paymentInitialTime = null;
        this.pollingTimeout = null;
        this.inactivityTimeout = null;
        this.queued = false;
        this.payment_stopped = false;
    }

    send_payment_request(cid) {
        super.send_payment_request(cid);
        return this._processPinelabs();
    }

    pendingPinelabsPaymentLine() {
        return this.pos.getPendingPaymentLine("pinelabs");
    }

    send_payment_cancel(order, cid) {
        super.send_payment_cancel(order, cid);
        return this._pinelabsCancel();
    }

    _callPinelabs(data, action) {
        return this.env.services.orm.silent
            .call("pos.payment.method", action, [[this.payment_method_id.id], data])
            .catch(this._handle_odoo_connection_failure.bind(this));
    }

    _handle_odoo_connection_failure(data = {}) {
        // handle timeout
        const line = this.pendingPinelabsPaymentLine();
        if (line) {
            line.set_payment_status("retry");
        }
        this._showError(
            _t(
                "Unable to connect to the Odoo server. Please check your internet connection and try again."
            )
        );

        return Promise.reject(data); // prevent subsequent unFulFilled's from being called
    }

    /**
     * This method processes the response from Pinelabs
     * when we request payment or cancellation.
     */
    async _pinelabsHandleResponse(response) {
        const line = this.pendingPinelabsPaymentLine();
        if (response.error) {
            line.set_payment_status("retry");
            this.payment_stopped
                ? this._showError(_t("Transaction failed due to inactivity"))
                : this._showError(response.error);
            this._removePaymentHandler(["transactionNumber", "plutusTransactionReferenceID"]);
            return Promise.resolve(false);
        }
        line.set_payment_status("waitingCard");
        localStorage.setItem("plutusTransactionReferenceID", response.plutusTransactionReferenceID);
        return await this._waitForPaymentToConfirm();
    }

    async _pinelabsCancel() {
        const line = this.pendingPinelabsPaymentLine();
        const data = {
            plutusTransactionReferenceID: localStorage.getItem("plutusTransactionReferenceID"),
            amount: line.amount * 100, // We need to provide the amount in paisa since Pine Labs processes amounts in paisa.
        };
        // We handle cancellation cases where the terminal responds with a `CANNOT CANCEL AS TRANSACTION IS IN PROGRESS` message.
        // In this scenario, we set a timeout for this.paymentInitialTime + CANCEL_REQUEST_TIME_LIMIT - Date.now() milliseconds for the second request.
        const response = await this._callPinelabs(data, "pinelabs_cancel_payment_request");
        if (response.errorMessage === "CANNOT CANCEL AS TRANSACTION IS IN PROGRESS") {
            this.pos.notification.add(
                _t("Your cancellation request is in the queue and will be processed shortly.")
            );
            clearTimeout(this.pollingTimeout);
            setTimeout(async () => {
                const response = await this._callPinelabs(data, "pinelabs_cancel_payment_request");
                if (response.responseCode) {
                    this.pos.notification.add(_t("Error: %s", response.errorMessage), {
                        title: _t("Warning"),
                        type: "danger",
                    });
                }
            }, this.paymentInitialTime + CANCEL_REQUEST_TIME_LIMIT - Date.now());
            return Promise.resolve(true);
        }
        if (response.errorMessage) {
            this._showError(response.errorMessage);
            return Promise.resolve(false);
        }
        this._pinelabsHandleResponse(response);
        return Promise.resolve(true);
    }

    async _processPinelabs() {
        const order = this.pos.get_order();
        const line = order.get_selected_paymentline();
        const sequenceNumber = order.payment_ids.filter(
            (pi) => pi.payment_method_id.use_payment_terminal === "pinelabs"
        ).length;
        if (line.amount < 0) {
            this._showError(_t("Cannot process transactions with negative amount."));
            return Promise.resolve();
        }

        const orderId = order?.pos_reference?.replace(" ", "").replaceAll("-", "").toUpperCase();
        const referencePrefix = this.pos.config.name.replace(/\s/g, "").slice(0, 4);
        localStorage.setItem(
            "transactionNumber",
            referencePrefix + "/" + orderId + "/" + crypto.randomUUID().replaceAll("-", "")
        );
        // Assume that the Pinelabs terminal payment method is configured with INR (Indian Rupees) as the currency_id in the POS config.
        // The conversion rate between INR and paisa is set as 1 INR = 100 paisa.
        const data = {
            amount: line.amount * 100, // We need to provide the amount in paisa since Pine Labs processes amounts in paisa.
            transactionNumber: localStorage.getItem("transactionNumber"),
            sequenceNumber: sequenceNumber, // In the case of multiple transactions for the same order, it is important to follow the correct sequence of transactions.
        };
        this.paymentInitialTime = Date.now();
        const response = await this._callPinelabs(data, "pinelabs_make_payment_request");
        return await this._pinelabsHandleResponse(response);
    }

    /**
     * Polling
     * This method uses the pinelabsFetchPaymentStatus function to check the payment status
     * every 10 seconds until it is resolved.
     */
    async _waitForPaymentToConfirm() {
        const paymentLine = this.pos.get_order().get_selected_paymentline();
        if (!paymentLine || paymentLine.payment_status == "retry") {
            return false;
        }
        const data = {
            plutusTransactionReferenceID: localStorage.getItem("plutusTransactionReferenceID"),
        };
        this._stop_pending_payment().then(() => (this.payment_stopped = true));
        const pinelabsFetchPaymentStatus = async (resolve, reject) => {
            //Clear the previous timeout before setting a new one
            clearTimeout(this.pollingTimeout);

            if (this.payment_stopped) {
                this._pinelabsCancel().then(() => {
                    paymentLine.set_payment_status("retry");
                    this.payment_stopped = false;
                });
                return resolve(false);
            }

            const response = await this._callPinelabs(data, "pinelabs_fetch_payment_status");

            if (![0, 1001].includes(response.responseCode)) {
                return this._pinelabsHandleResponse(response);
            }
            const resultStatus = response?.status;

            if (resultStatus === "TXN UPLOADED" && this.queued === false) {
                this.queued = true;
            }
            if (
                resultStatus === "TXN APPROVED" &&
                response?.plutusTransactionReferenceID !==
                    parseInt(localStorage.getItem("plutusTransactionReferenceID"))
            ) {
                return this._pinelabsHandleResponse({ error: _t("Reference number mismatched") });
            } else if (resultStatus === "TXN APPROVED") {
                const data = response.data;
                paymentLine.payment_method_issuer_bank = data["Acquirer Name"];
                paymentLine.payment_method_authcode = data["ApprovalCode"];
                paymentLine.cardholder_name = data["Card Holder Name"];
                paymentLine.card_no = data["Card Number"]?.slice(-4) || "";
                paymentLine.card_brand = data["Card Type"];
                paymentLine.payment_method_payment_mode = data["PaymentMode"];
                paymentLine.payment_ref_no = localStorage.getItem("transactionNumber");
                paymentLine.transaction_id = data["TransactionLogId"];
                paymentLine.payment_date = this._getPaymentDate(
                    data["Transaction Date"],
                    data["Transaction Time"]
                );
                this._removePaymentHandler(["transactionNumber", "plutusTransactionReferenceID"]);
                return resolve(response);
            } else {
                this.pollingTimeout = setTimeout(
                    pinelabsFetchPaymentStatus,
                    REQUEST_TIMEOUT,
                    resolve,
                    reject
                );
            }
        };
        return new Promise(pinelabsFetchPaymentStatus);
    }

    _getPaymentDate(dateString, timeString) {
        // The dateString value is formatted as `03122024`, while the timeString value appears as `063515`.
        // First, we format the DateTime string to create a DateTime object.
        const formattedDateTimeString = `${dateString.substring(4, 8)}-${dateString.substring(
            2,
            4
        )}-${dateString.substring(0, 2)}T${timeString.substring(0, 2)}:${timeString.substring(
            2,
            4
        )}:${timeString.substring(4, 6)}Z`;
        const utcDate = new DateTime(formattedDateTimeString);
        return serializeDateTime(utcDate);
    }

    _stop_pending_payment() {
        return new Promise(
            (resolve) => (this.inactivityTimeout = setTimeout(resolve, CANCEL_REQUEST_TIME_LIMIT))
        );
    }

    _removePaymentHandler(payment_data) {
        this.pos.mainScreen.component.name === "PaymentScreen" &&
            payment_data.forEach((data) => {
                localStorage.removeItem(data);
            });
        clearTimeout(this.pollingTimeout);
        clearTimeout(this.inactivityTimeout);
        this.queued = this.payment_stopped = false;
    }

    _showError(error_msg, title) {
        this.env.services.dialog.add(AlertDialog, {
            title: title || _t("Pine Labs Error"),
            body: error_msg,
        });
    }
}
