import { register_payment_method } from "@point_of_sale/app/services/pos_store";
import { handleRPCError, offlineErrorHandler } from "@point_of_sale/app/utils/error_handlers";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { serializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { ConnectionLostError, RPCError } from "@web/core/network/rpc";
import { isNull } from "@web/views/utils";

const POLLING_REQUEST_MS = 3 * 1000; // 3 seconds
const CANCEL_REQUEST_TIME_LIMIT_MS = 3 * 60 * 1000; // 3 minutes
const WAIT_BEFORE_RESULT_FETCH = 3 * 1000; // 3 seconds
const { DateTime } = luxon;

export class PaymentDPOPay extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.pollingTimeout = null;
        this.inactivityTimeout = null;
        this.paymentStopped = false;
        this.pollingInProgress = false;
    }

    sendPaymentRequest(cid) {
        super.sendPaymentRequest(cid);
        return this._processPaymentRequest();
    }

    sendPaymentCancel(order, cid) {
        super.sendPaymentCancel(order, cid);
        return this._cancelPaymentRequest({
            sourceId: order.getSelectedPaymentline().transaction_id,
        });
    }

    async _processPaymentRequest() {
        const order = this.pos.getOrder();
        const paymentLine = order.getSelectedPaymentline();
        if (paymentLine.amount <= 0) {
            this._handleError(undefined, _t("Transaction amount must be greater than zero."));
            return false;
        }

        const isReady = await this._checkTerminalStatus();

        if (!isReady) {
            return false;
        }

        if (paymentLine.transaction_id) {
            // Possible return values: true, false, null
            const recoveryStatus = await this._attemptTransactionRecovery(paymentLine);

            //  null  → API call failed or could not retrieve transaction status
            if (isNull(recoveryStatus)) {
                return false;
            }

            if (recoveryStatus) {
                return true;
            }
        }

        const orderId = order?.pos_reference?.replace(" ", "").replaceAll("-", "").toUpperCase();
        const referencePrefix = this.pos.config.name.replace(/\s/g, "").slice(0, 4);
        paymentLine.transaction_id =
            referencePrefix + "/" + orderId + "/" + crypto.randomUUID().replaceAll("-", "");

        const currency = paymentLine.pos_order_id.currency;
        const data = {
            currency: currency.iso_numeric.toString(),
            amount: Math.round(
                paymentLine.amount * Math.pow(10, currency.decimal_places)
            ).toString(), // Convert amount to smallest currency unit
            sourceId: paymentLine.transaction_id,
        };

        const response = await this._callDpoPayMakeRequest(data, "start-transaction");
        return await this._makePaymentRequestHandler(response);
    }

    async _makePaymentRequestHandler(response) {
        const line = this._pendingDPOPaymentLine();
        if (!response || response?.errorMessage || !line) {
            this._handleError(response, _t("Unable to initiate DPO payment. Please try again."));
            return false;
        }
        this.pollingInProgress = true;
        line.setPaymentStatus("waitingCard");
        return await this._waitForPaymentToConfirm();
    }

    async _waitForPaymentToConfirm() {
        const paymentLine = this.pos.getOrder().getSelectedPaymentline();
        if (!paymentLine || paymentLine.payment_status === "retry") {
            return false;
        }

        const data = { sourceId: paymentLine.transaction_id };
        this._stopPendingPayment().then(() => (this.paymentStopped = true));

        const dpopayFetchPaymentStatus = async (resolve, reject) => {
            clearTimeout(this.pollingTimeout);

            if (this.pos.router.state.current !== "PaymentScreen") {
                this._removePaymentHandler();
                return;
            }

            if (this.paymentStopped) {
                await this._cancelPaymentRequest(data);
                paymentLine.setPaymentStatus("retry");
                return resolve(false);
            }

            if (paymentLine.payment_status === "retry") {
                return resolve(false);
            }

            const response = await this._callDpoPayMakeRequest(data, "get-status");
            return this._paymentStatusRequestHandler(
                response,
                dpopayFetchPaymentStatus,
                resolve,
                reject
            );
        };

        return new Promise(dpopayFetchPaymentStatus);
    }

    async _attemptTransactionRecovery(paymentLine) {
        const data = { sourceId: paymentLine.transaction_id };

        const statusResponse = await this._callDpoPayMakeRequest(data, "get-status");
        if (!statusResponse || statusResponse.errorMessage) {
            if (statusResponse.errorMessage === "Transaction not found") {
                return false;
            }
            this._handleError(statusResponse, _t("Failed to retrieve payment status."));
            return null;
        }
        if (!statusResponse.success) {
            return false;
        }

        const resultResponse = await this._callDpoPayMakeRequest(data, "get-result");
        if (!resultResponse || resultResponse.errorMessage) {
            this._handleError(resultResponse, _t("Failed to fetch last transaction result."));
            return null;
        }
        if (!resultResponse.success) {
            return false;
        }

        this._saveTransactionResult(paymentLine, resultResponse);
        return true;
    }

    async _checkTerminalStatus() {
        const response = await this._callDpoPayMakeRequest({}, "get-status");

        if (!response || response.errorMessage) {
            this._handleError(response, _t("Unable to reach DPO Pay terminal."));
            return false;
        }

        if (response.displayText === "NO TXN / SYSTEM IDLE") {
            return true;
        }

        return false;
    }

    async _paymentStatusRequestHandler(response, callBack, resolve, reject) {
        const line = this.pos.getOrder().getSelectedPaymentline();

        if (!response || response?.errorMessage) {
            this._handleError(
                response,
                _t("Failed to retrieve payment status."),
                response ? "retry" : "force_done"
            );
            return response ? resolve(false) : undefined;
        }

        if (response.offline) {
            this._handleError(response, _t("DPO Pay terminal is currently offline."));
            return resolve(false);
        }

        if (response.declined) {
            this._handleError(response, _t("Payment is declined by DPO Pay."));
            return resolve(false);
        }

        if (response.complete && !response.success) {
            this._handleError(response, _t("Payment is unsuccessful."));
            return resolve(false);
        }

        if (response.complete) {
            // Wait 3 seconds for DPO Pay to finalize the payment result.
            await new Promise((resolve) => setTimeout(resolve, WAIT_BEFORE_RESULT_FETCH));

            const resp = await this._callDpoPayMakeRequest(
                { sourceId: response.sourceid },
                "get-result"
            );

            if (!resp?.success) {
                this._handleError(
                    resp,
                    _t("Failed to retrieve transaction result."),
                    resp ? "retry" : "force_done"
                );
                return resp ? resolve(false) : undefined;
            }
            this._saveTransactionResult(line, resp);
            return resolve(response);
        }

        this.pollingTimeout = setTimeout(callBack, POLLING_REQUEST_MS, resolve, reject);
    }

    async _saveTransactionResult(line, data) {
        const paymentMode = data.dataMap?.MNO;
        const updatedData = {
            payment_method_issuer_bank: data["Acquirer Name"],
            payment_method_authcode: data["authCode"],
            cardholder_name: data["CardHolderName"],
            card_no: data["panMasked"]?.slice(-4),
            card_brand: data["cardType"],
            payment_method_payment_mode: paymentMode ? `${paymentMode} Mobile Money` : "CARD",
            dpopay_rrn: data["rrn"],
            payment_date: this._getPaymentDate(data["TransactionDate"], data["TransactionTime"]),
        };

        if (data.dataMap) {
            updatedData.dpopay_transaction_ref = data.dataMap["Transaction Ref"];
            updatedData.dpopay_mobile_money_phone = data.dataMap["Phone Number"]?.slice(-4);
        }

        line.update(updatedData);
        this._removePaymentHandler();
    }

    async _cancelPaymentRequest(data) {
        const response = await this._callDpoPayMakeRequest(data, "cancel-transaction");
        return await this._paymentCancelRequestHandler(response);
    }

    async _paymentCancelRequestHandler(response) {
        if (response?.responseCode) {
            this._removePaymentHandler();
            return true;
        }

        this._showAlert(response?.errorMessage ?? _t("Failed to cancel payment."));
        return !this.pollingInProgress;
    }

    async _callDpoPayMakeRequest(data, action) {
        try {
            return await this.pos.data.call("pos.payment.method", "send_dpopay_request", [
                [this.payment_method_id.id],
                data,
                action,
            ]);
        } catch (error) {
            const line = this._pendingDPOPaymentLine();
            this.pos.paymentTerminalInProgress = false;
            if (line) {
                line.setPaymentStatus("force_done");
            }

            if (error instanceof ConnectionLostError) {
                offlineErrorHandler(this.env, error, error);
            } else if (error instanceof RPCError) {
                handleRPCError(error, this.pos.dialog);
            } else {
                throw error;
            }
        }
    }

    _pendingDPOPaymentLine() {
        return this.pos.getPendingPaymentLine("dpopay");
    }

    _getPaymentDate(dateString, timeString) {
        return serializeDateTime(
            DateTime.fromFormat(`${dateString} ${timeString}`, "dd/MM/yyyy HH:mm")
        );
    }

    _handleError(response, fallbackMessage, status = "retry") {
        const line = this._pendingDPOPaymentLine();
        if (line) {
            line.setPaymentStatus(status);
        }

        this._removePaymentHandler();
        this._showAlert(response?.errorMessage ?? fallbackMessage);
    }

    _showAlert(message, title) {
        this.pos.dialog.add(AlertDialog, {
            title: title || _t("Dpo Pay Error"),
            body: message,
        });
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
        this.paymentStopped = false;
        this.pollingInProgress = false;
    }
}

register_payment_method("dpopay", PaymentDPOPay);
