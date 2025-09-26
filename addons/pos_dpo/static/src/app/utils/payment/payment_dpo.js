import { register_payment_method } from "@point_of_sale/app/services/pos_store";
import { handleRPCError, offlineErrorHandler } from "@point_of_sale/app/utils/error_handlers";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { serializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { ConnectionLostError, RPCError } from "@web/core/network/rpc";

const POLLING_REQUEST_MS = 10 * 1000; // 10 seconds
const CANCEL_REQUEST_TIME_LIMIT_MS = 10 * 60 * 1000; // 10 minutes
const { DateTime } = luxon;

const DPO_ACTIONS = {
    START: "start-transaction",
    CANCEL: "cancel-transaction",
    STATUS: "get-status",
    RESULT: "get-result",
};

export class PaymentDPO extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.pollingTimeout = null;
        this.inactivityTimeout = null;
        this.paymentStopped = false;
    }

    /**
     * @override
     */
    sendPaymentRequest(cid) {
        super.sendPaymentRequest(cid);
        return this._processPaymentRequest();
    }

    _pendingDPOPaymentLine() {
        return this.pos.getPendingPaymentLine("dpo");
    }

    /**
     * @override
     */
    sendPaymentCancel(order, cid) {
        super.sendPaymentCancel(order, cid);
        return this._cancelPaymentRequest({
            sourceId: order.getSelectedPaymentline().transaction_id,
        });
    }

    async _callDpoMakeRequest(data, action) {
        try {
            return await this.pos.data.call("pos.payment.method", "send_dpo_request", [
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
                handleRPCError(error, this.env.services.dialog);
            } else {
                throw error;
            }
        }
    }

    _handleError(response, fallbackMessage, status = "retry") {
        const line = this._pendingDPOPaymentLine();
        if (line) {
            line.setPaymentStatus(status);
        }

        const message =
            response && typeof response.errorMessage === "string" && response.errorMessage.trim()
                ? response.errorMessage
                : _t(fallbackMessage);
        this._removePaymentHandler();
        this.pos.notification.add(message, { type: "danger", sticky: false });
    }

    async _makePaymentRequestHandler(response) {
        const line = this._pendingDPOPaymentLine();
        if (!response || response?.errorMessage) {
            this._handleError(response, "DPO make payment request failed");
            return false;
        }

        line.setPaymentStatus("waitingCard");
        return await this._waitForPaymentToConfirm();
    }

    async _paymentStatusRequestHandler(response, callBack, resolve, reject) {
        const line = this.pos.getOrder().getSelectedPaymentline();

        if (!response || response?.errorMessage) {
            this._handleError(
                response,
                "DPO get payment status request failed",
                response ? "retry" : "force_done"
            );
            return resolve(false);
        }

        if (response.offline) {
            this._handleError(response, "DPO payment is offline");
            return resolve(false);
        }

        if (response.declined) {
            this._handleError(response, "DPO payment is declined");
            return resolve(false);
        }

        if (response.complete && !response.success) {
            this._handleError(response, "DPO payment is Failed");
            return resolve(false);
        }

        if (response.complete) {
            const resp = await this._callDpoMakeRequest(
                { sourceId: response.sourceid },
                DPO_ACTIONS.RESULT
            );
            if (!resp.success) {
                this._handleError(response, "DPO payment is failed");
                return resolve(response);
            }

            const paymentMode = resp?.dataMap?.MNO;
            const updatedData = {
                payment_method_issuer_bank: resp["Acquirer Name"],
                payment_method_authcode: resp["authCode"],
                cardholder_name: resp["CardHolderName"],
                card_no: resp["panMasked"]?.slice(-4),
                dpo_receipt_number: resp["ReceiptNo"],
                card_brand: resp["cardType"],
                payment_method_payment_mode: paymentMode ? `${paymentMode} Mobile Money` : "CARD",
                dpo_rrn: resp["rrn"],
                payment_date: this._getPaymentDate(
                    resp["TransactionDate"],
                    resp["TransactionTime"]
                ),
            };

            if (resp?.dataMap) {
                updatedData.dpo_transaction_ref = resp.dataMap["Transaction Ref"];
                updatedData.dpo_mobile_money_phone = resp.dataMap["Phone Number"]?.slice(-4);
            }

            line.update(updatedData);
            this._removePaymentHandler();
            return resolve(response);
        }

        this.pollingTimeout = setTimeout(callBack, POLLING_REQUEST_MS, resolve, reject);
    }

    _paymentCancelRequestHandler(response) {
        if (!response || response?.errorMessage) {
            this._handleError(response, "DPO payment cancellation request failed");
            return false;
        }

        if (response.responseCode) {
            if (this.paymentStopped) {
                this._handleError(response, "Transaction failed due to inactivity");
            } else {
                this.pos.notification.add(response.responseMessage, {
                    type: "warning",
                    sticky: false,
                });
            }
            this._removePaymentHandler();
            return true;
        }

        return false;
    }

    async _processPaymentRequest() {
        const order = this.pos.getOrder();
        const paymentLine = order.getSelectedPaymentline();
        if (paymentLine.amount <= 0) {
            this._handleError(
                undefined,
                "Cannot process transactions with zero or negative amount."
            );
            return false;
        }

        const orderId = order?.pos_reference?.replace(" ", "").replaceAll("-", "").toUpperCase();
        const referencePrefix = this.pos.config.name.replace(/\s/g, "").slice(0, 4);
        paymentLine.update({
            transaction_id: referencePrefix + orderId + crypto.randomUUID().replaceAll("-", ""),
        });

        const currency = paymentLine.pos_order_id.currency;
        const data = {
            currencyCode: currency.iso_numeric.toString(),
            amount: Math.round(
                paymentLine.amount * Math.pow(10, currency.decimal_places)
            ).toString(),
            sourceId: paymentLine.transaction_id,
        };
        const response = await this._callDpoMakeRequest(data, DPO_ACTIONS.START);
        return await this._makePaymentRequestHandler(response);
    }

    async _cancelPaymentRequest(data) {
        const response = await this._callDpoMakeRequest(data, DPO_ACTIONS.CANCEL);
        return this._paymentCancelRequestHandler(response);
    }

    async _waitForPaymentToConfirm() {
        const paymentLine = this.pos.getOrder().getSelectedPaymentline();
        if (!paymentLine || paymentLine.payment_status === "retry") {
            return false;
        }

        const data = { sourceId: paymentLine.transaction_id };
        this._stopPendingPayment().then(() => (this.paymentStopped = true));

        const dpoFetchPaymentStatus = async (resolve, reject) => {
            clearTimeout(this.pollingTimeout);

            if (this.pos.router.state.current !== "PaymentScreen") {
                this._removePaymentHandler();
                return;
            }

            if (this.paymentStopped) {
                await this._cancelPaymentRequest(data);
                paymentLine.setPaymentStatus("retry");
                this.paymentStopped = false;
                return resolve(false);
            }

            if (paymentLine.payment_status === "retry") {
                return resolve(false);
            }

            const response = await this._callDpoMakeRequest(data, DPO_ACTIONS.STATUS);
            return this._paymentStatusRequestHandler(
                response,
                dpoFetchPaymentStatus,
                resolve,
                reject
            );
        };

        return new Promise(dpoFetchPaymentStatus);
    }

    _getPaymentDate(dateString, timeString) {
        const localDate = DateTime.fromFormat(`${dateString} ${timeString}`, "dd/MM/yyyy HH:mm");
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
        this.paymentStopped = false;
    }
}

register_payment_method("dpo", PaymentDPO);
