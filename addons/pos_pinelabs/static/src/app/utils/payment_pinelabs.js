import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { serializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";

const CANCEL_REQUEST_TIME_LIMIT = 125000;
const { DateTime } = luxon;

export class PaymentPinelabs extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.paymentInitialTime = null;
        this.paymentLineResolvers = {};
        this.offlineErrorHandler = registry.category("error_handlers").get("offlineErrorHandler");
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
        return this.pos.data
            .call("pos.payment.method", action, [[this.payment_method_id.id], data])
            .catch((error) => {
                const line = this.pendingPinelabsPaymentLine();
                if (line) {
                    line.set_payment_status("retry");
                }
                this.offlineErrorHandler(this.env, error, error);
            });
    }

    /**
     * This method processes the response from Pinelabs
     * when we request payment or cancellation.
     */
    async _pinelabsHandleResponse(response) {
        const line = this.pendingPinelabsPaymentLine();
        if (!response || response.error) {
            line.set_payment_status("retry");
            response.error ? this._showError(response.error) : null;
            return false;
        }
        line.set_payment_status("waitingCard");
        line.plutus_transaction_reference = response.plutusTransactionReferenceID;
        return await this._waitForPaymentToConfirm();
    }

    async _pinelabsCancel() {
        const line = this.pendingPinelabsPaymentLine();
        const data = {
            plutusTransactionReferenceID: line.plutus_transaction_reference,
            amount: line.amount * 100, // We need to provide the amount in paisa since Pine Labs processes amounts in paisa.
        };
        // We handle cancellation cases where the terminal responds with a `CANNOT CANCEL AS TRANSACTION IS IN PROGRESS` message.
        // In this scenario, we set a timeout for this.paymentInitialTime + CANCEL_REQUEST_TIME_LIMIT - Date.now() milliseconds for the second request.
        const response = await this._callPinelabs(data, "pinelabs_cancel_payment_request");
        if (response.responseCode === 11) {
            this.pos.notification.add(
                _t("Your cancellation request is in the queue and will be processed shortly.")
            );
            setTimeout(async () => {
                const response = await this._callPinelabs(data, "pinelabs_cancel_payment_request");
                if (response.responseCode) {
                    this.pos.notification.add(_t("Error: %s", response.errorMessage), {
                        title: _t("Warning"),
                        type: "danger",
                    });
                }
            }, this.paymentInitialTime + CANCEL_REQUEST_TIME_LIMIT - Date.now());
            return true;
        }
        if (response.errorMessage) {
            this._showError(response.errorMessage);
            return false;
        }
        this._pinelabsHandleResponse(response);
        return true;
    }

    async _processPinelabs() {
        const order = this.pos.get_order();
        const paymentLine = order.get_selected_paymentline();
        const sequenceNumber = order.payment_ids.filter(
            (pi) => pi.payment_method_id.use_payment_terminal === "pinelabs"
        ).length;
        if (paymentLine.amount < 0) {
            this._showError(_t("Cannot process transactions with negative amount."));
            return false;
        }

        const orderId = order?.pos_reference?.replace(" ", "").replaceAll("-", "").toUpperCase();
        const referencePrefix = this.pos.config.name.replace(/\s/g, "").slice(0, 4);
        paymentLine.payment_ref_no =
            referencePrefix + "/" + orderId + "/" + crypto.randomUUID().replaceAll("-", "");

        // Assume that the Pinelabs terminal payment method is configured with INR (Indian Rupees) as the currency_id in the POS config.
        // The conversion rate between INR and paisa is set as 1 INR = 100 paisa.
        const data = {
            amount: paymentLine.amount * 100, // We need to provide the amount in paisa since Pine Labs processes amounts in paisa.
            transactionNumber: paymentLine.payment_ref_no,
            sequenceNumber: sequenceNumber, // In the case of multiple transactions for the same order, it is important to follow the correct sequence of transactions.
        };
        this.paymentInitialTime = Date.now();
        const response = await this._callPinelabs(data, "pinelabs_make_payment_request");
        return await this._pinelabsHandleResponse(response);
    }

    async _waitForPaymentToConfirm() {
        const paymentLine = this.pos.get_order().get_selected_paymentline();
        if (!paymentLine || paymentLine.payment_status == "retry") {
            return false;
        }
        const data = {
            plutusTransactionReferenceID: paymentLine.plutus_transaction_reference,
            config_id: this.pos.get_order().config_id.id,
            payment_method_id: this.payment_method_id.id,
            amount: paymentLine.amount * 100,
        };
        await this._callPinelabs(data, "pinelabs_fetch_payment_status");
        return new Promise((resolve) => {
            this.paymentLineResolvers[this.pendingPinelabsPaymentLine().uuid] = resolve;
        });
    }

    handlePinelabsPaymentResponse(response) {
        const paymentLine = this.pos.get_order().get_selected_paymentline();
        if (!paymentLine || paymentLine.payment_status == "retry") {
            return;
        }
        if (response.error) {
            return this._pinelabsHandleResponse(response);
        }
        let isPaymentSuccessful = false;
        if (
            response.responseCode === 0 &&
            response.plutusTransactionReferenceID !== paymentLine.plutus_transaction_reference
        ) {
            return this._pinelabsHandleResponse({ error: _t("Reference number mismatched") });
        } else if (response.responseCode === 0) {
            const data = response.data;
            isPaymentSuccessful = true;
            paymentLine.payment_method_issuer_bank = data["Acquirer Name"];
            paymentLine.payment_method_authcode = data["ApprovalCode"];
            paymentLine.cardholder_name = data["Card Holder Name"];
            paymentLine.card_no = data["Card Number"]?.slice(-4) || "";
            paymentLine.card_brand = data["Card Type"];
            paymentLine.payment_method_payment_mode = data["PaymentMode"];
            paymentLine.transaction_id = data["TransactionLogId"];
            paymentLine.payment_date = this._getPaymentDate(
                data["Transaction Date"],
                data["Transaction Time"]
            );
            paymentLine.set_payment_status("done");
        }
        const resolver = this.paymentLineResolvers?.[paymentLine.uuid];
        if (resolver) {
            resolver(isPaymentSuccessful);
        } else {
            paymentLine.handle_payment_response(isPaymentSuccessful);
        }
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

    _showError(error_msg, title) {
        this.env.services.dialog.add(AlertDialog, {
            title: title || _t("Pine Labs Error"),
            body: error_msg,
        });
    }
}
