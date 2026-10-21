import { _t } from "@web/core/l10n/translation";
import { PaymentInterfaceV2 } from "@point_of_sale/app/utils/payment/payment_interface_v2";
import { registry } from "@web/core/registry";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
const { DateTime } = luxon;

export class PaymentAdyen extends PaymentInterfaceV2 {
    setup() {
        super.setup(...arguments);
        this.use_polling = true;
        this.title_error = _t("Adyen Error");
        this.connectWebhook("ADYEN_LATEST_RESPONSE", PaymentAdyen);
    }

    // ----- Payment Request -----

    /**
     * Sends the payment (or the reversal of a refund) to the terminal, with
     * a new ServiceID kept on the line: answers, status reads and the abort
     * name the payment by it. A timeout counts as sent (the terminal may have
     * received it): the line waits for the answer, with a warning.
     *
     * @returns {Promise} false when not sent (refused, or not an Adyen
     * refund), otherwise `request.wait("waiting_card")`
     */
    async sendPaymentRequest(line, request) {
        if (line.isRefund && !line.uiState.adyenRefundTransactionId) {
            this.showError(_t("Cannot refund non-Adyen transactions via Adyen."));
            return false;
        }

        const data = line.isRefund ? this._adyenReversalData(line) : this._adyenPayData(line);
        line.uiState.adyenTerminalServiceId = data.SaleToPOIRequest.MessageHeader.ServiceID;
        const response = await this._callAdyen(data);
        if (response?.error?.timeout) {
            this.notification.add(
                _t(
                    "Adyen is slow to answer. Check the terminal: the payment may still go through."
                ),
                { type: "warning" }
            );
        }
        if (!this._isRequestAccepted(response)) {
            return false;
        }
        return request.wait("waiting_card");
    }

    /**
     * Reads the PaymentResponse (or ReversalResponse) of a webhook or status
     * read: when successful, sets the transaction id, card and tip on the
     * line, otherwise shows Adyen's message. false (not sent, or not found
     * by the status read) means retry.
     */
    async handlePaymentResponse(line, response) {
        if (!response) {
            return super.handlePaymentResponse(...arguments);
        }
        const paymentResponse = this._paymentResponse(response);
        const additionalResponse = new URLSearchParams(paymentResponse.Response.AdditionalResponse);
        const isPaymentSuccessful = this.isPaymentSuccessful(line, response);
        if (isPaymentSuccessful) {
            await this.handleSuccessResponse(line, paymentResponse, additionalResponse);
        } else {
            this.showError(_t("Message from Adyen: %s", additionalResponse.get("message")));
        }
        return super.handlePaymentResponse(line, isPaymentSuccessful);
    }

    /**
     * Whether the response is a success for the last request of the line:
     * its ServiceID must match, an answer to an older request is not.
     */
    isPaymentSuccessful(line, response) {
        if (!response) {
            return false;
        }
        const paymentResponse = this._paymentResponse(response);
        return (
            response.header.ServiceID === line.uiState.adyenTerminalServiceId &&
            paymentResponse.Response.Result === "Success"
        );
    }

    _paymentResponse(response) {
        return response.body.PaymentResponse ?? response.body.ReversalResponse;
    }

    async handleSuccessResponse(line, payment_response, additional_response) {
        line.transaction_id = payment_response.POIData.POITransactionID.TransactionID;
        line.card_type = additional_response.get("cardType");
        line.cardholder_name = additional_response.get("cardHolderName") || "";

        const payment_result = payment_response.PaymentResult;
        const tip_amount = payment_result?.AmountsResp?.TipAmount ?? 0;
        if (this.pos.config.adyen_ask_customer_for_tip && tip_amount > 0) {
            await this.pos.setTip(tip_amount, "fixed", false, line.pos_order_id);
            line.setAmount(payment_result.AmountsResp.AuthorizedAmount);
        }
    }

    // ----- Payment Cancel -----

    async sendPaymentCancel(line) {
        if (!line.uiState.adyenTerminalServiceId) {
            // Sent from another device: the abort can't name the payment
            return this._confirmCancelOnTerminal();
        }
        // Only valid response is a 200 OK HTTP response which is
        // represented by true.
        return (await this._callAdyen(this._adyenAbortData(line))) === true;
    }

    async handlePaymentCancelResponse(line, response, previousStatus) {
        if (response === false) {
            this.showError(
                _t(
                    "Cancelling the payment failed. Please cancel it manually on the payment terminal."
                )
            );
        }
        return super.handlePaymentCancelResponse(...arguments);
    }

    _confirmCancelOnTerminal() {
        return new Promise((resolve) => {
            this.dialog.add(ConfirmationDialog, {
                title: this.title_error,
                body: _t(
                    "This payment was sent from another device, so it can't be cancelled from here. Cancel it on the payment terminal, then confirm."
                ),
                confirmLabel: _t("Cancelled on the terminal"),
                confirm: () => resolve(true),
                cancel: () => resolve(null),
            });
        });
    }

    // ----- Payment Adjust -----

    canBeAdjusted(line) {
        return ["mc", "visa", "amex", "discover"].includes(line.card_type);
    }

    async sendPaymentAdjust(line) {
        return this._callAdyen(this._adyenAdjustData(line), "adjust");
    }

    async handlePaymentAdjustResponse(line, response, previousAmount) {
        // Adyen answers an accepted adjustment with this exact value, an
        // error with a JSON holding a message.
        const isAdjustSuccessful = response?.response === "[adjustAuthorisation-received]";
        if (!isAdjustSuccessful) {
            this.showError(
                _t("Adjusting the amount failed. Message from Adyen: %s", response?.message)
            );
        }
        return super.handlePaymentAdjustResponse(line, isAdjustSuccessful, previousAmount);
    }

    // ----- Waiting For The Response -----

    /**
     * Reads the status of the last request of the line.
     *
     * @returns {Promise} the answer when there is a result; false (retry)
     * when Adyen doesn't know the request (NotFound) or replies with an
     * error; undefined while in progress. Rejected when the call fails (a
     * failed poll).
     */
    async pollPaymentStatus(line) {
        const response = await this._callAdyen(this._adyenStatusData(line), "payment_status");
        if (response?.error) {
            this.showError(_t("Authentication failed. Please check your Adyen credentials."));
            return false;
        }
        const transactionStatus = response?.SaleToPOIResponse?.TransactionStatusResponse;
        if (transactionStatus?.Response.Result === "Success") {
            const repeatedMessage = transactionStatus.RepeatedMessageResponse;
            return {
                header: repeatedMessage.MessageHeader,
                body: repeatedMessage.RepeatedResponseMessageBody,
            };
        }
        if (transactionStatus?.Response.ErrorCondition === "NotFound") {
            return false;
        }
    }

    /**
     * Only a line with a ServiceID can be restored: without it (sent from
     * another device), no answer or status read can name the payment, so the
     * line waits for the cashier to cancel or force it.
     */
    restorePendingRequest(line) {
        if (!line.uiState.adyenTerminalServiceId) {
            return;
        }
        return super.restorePendingRequest(...arguments);
    }

    /**
     * Reads the latest answer Adyen sent to this payment method and gives it
     * to the line with its ServiceID, see answerRequest(). When it can't be
     * read, the line keeps waiting: the next poll or webhook answers. The
     * line can be settled already (late answer, see handleLateResponse()).
     */
    async onWebhookNotification() {
        let notification;
        try {
            notification = await this.callPaymentMethod("get_latest_adyen_status", [
                [this.payment_method_id.id],
            ]);
        } catch {
            return;
        }
        const response = notification?.SaleToPOIResponse;
        if (!response) {
            return;
        }
        const line = this.pos.models["pos.payment"].find(
            (line) =>
                line.payment_interface === this &&
                line.uiState.adyenTerminalServiceId === response.MessageHeader.ServiceID
        );
        if (line) {
            this.answerRequest(line, { header: response.MessageHeader, body: response });
        }
    }

    // ----- Adyen Requests -----

    _callAdyen(data, operation = false) {
        return this.callPaymentMethod("proxy_adyen_request", [
            [this.payment_method_id.id],
            data,
            operation,
        ]);
    }

    _isRequestAccepted(response) {
        if (response?.error?.timeout) {
            // Maybe received by Adyen: the status read or the webhook tells
            return true;
        }

        if (!response || (response.error && [401, 403].includes(response.error.status_code))) {
            this.showError(_t("Authentication failed. Please check your Adyen credentials."));
            return false;
        }

        response = response.SaleToPOIRequest;
        if (response?.EventNotification?.EventToNotify === "Reject") {
            logPosMessage("PaymentAdyen", "_isRequestAccepted", `Error from Adyen`, false, [
                response,
            ]);
            const params = new URLSearchParams(response.EventNotification.EventDetails);
            this.showError(
                _t("An unexpected error occurred. Message from Adyen: %s", params.get("message"))
            );
            return false;
        }
        return true;
    }

    _adyenGetSaleId() {
        var config = this.pos.config;
        return `${config.display_name} (ID: ${config.id})`;
    }

    _adyenCommonMessageHeader() {
        // random ID to identify request/response pairs, max length is 10
        const serviceId = Math.floor(Math.random() * Math.pow(2, 64))
            .toString()
            .substring(0, 10);

        return {
            ProtocolVersion: "3.0",
            MessageClass: "Service",
            MessageType: "Request",
            SaleID: this._adyenGetSaleId(),
            ServiceID: serviceId,
            POIID: this.payment_method_id.adyen_terminal_identifier,
        };
    }

    _adyenPayData(line) {
        const order = line.pos_order_id;
        const config = this.pos.config;
        var data = {
            SaleToPOIRequest: {
                MessageHeader: Object.assign(this._adyenCommonMessageHeader(), {
                    MessageCategory: "Payment",
                }),
                PaymentRequest: {
                    SaleData: {
                        SaleTransactionID: {
                            TransactionID: `${order.uuid}--${order.session_id.id}`,
                            TimeStamp: DateTime.now().toFormat("yyyy-MM-dd'T'HH:mm:ssZZ"), // iso format: '2018-01-10T11:30:15+00:00'
                        },
                    },
                    PaymentTransaction: {
                        AmountsReq: {
                            Currency: this.pos.currency.name,
                            RequestedAmount: line.amount,
                        },
                    },
                },
            },
        };

        data.SaleToPOIRequest.PaymentRequest.SaleData.SaleToAcquirerData =
            config.adyen_ask_customer_for_tip
                ? "tenderOption=AskGratuity&authorisationType=PreAuth"
                : "authorisationType=PreAuth";

        return data;
    }

    _adyenReversalData(line) {
        const order = line.pos_order_id;
        return {
            SaleToPOIRequest: {
                MessageHeader: Object.assign(this._adyenCommonMessageHeader(), {
                    MessageCategory: "Reversal",
                }),
                ReversalRequest: {
                    ReversalReason: "MerchantCancel",
                    ReversedAmount: Math.abs(line.amount),
                    OriginalPOITransaction: {
                        POITransactionID: {
                            TransactionID: line.uiState.adyenRefundTransactionId,
                            TimeStamp: line.uiState.adyenRefundTransactionTimestamp,
                        },
                    },
                    SaleData: {
                        SaleToAcquirerData: `currency=${this.pos.currency.name}`,
                        SaleTransactionID: {
                            TransactionID: `${order.uuid}--${order.session_id.id}`,
                            TimeStamp: DateTime.utc().toISO(),
                        },
                    },
                },
            },
        };
    }

    _adyenAbortData(line) {
        return {
            SaleToPOIRequest: {
                MessageHeader: Object.assign(this._adyenCommonMessageHeader(), {
                    MessageCategory: "Abort",
                }),
                AbortRequest: {
                    AbortReason: "MerchantAbort",
                    MessageReference: {
                        MessageCategory: "Payment",
                        SaleID: this._adyenGetSaleId(),
                        ServiceID: line.uiState.adyenTerminalServiceId,
                    },
                },
            },
        };
    }

    _adyenAdjustData(line) {
        return {
            originalReference: line.transaction_id,
            modificationAmount: {
                value: parseInt(line.amount * Math.pow(10, this.pos.currency.decimal_places)),
                currency: this.pos.currency.name,
            },
            merchantAccount: this.payment_method_id.adyen_merchant_account,
            additionalData: {
                industryUsage: "DelayedCharge",
            },
        };
    }

    _adyenStatusData(line) {
        return {
            SaleToPOIRequest: {
                MessageHeader: Object.assign(this._adyenCommonMessageHeader(), {
                    MessageCategory: "TransactionStatus",
                }),
                TransactionStatusRequest: {
                    ReceiptReprintFlag: true,
                    DocumentQualifier: ["CustomerReceipt", "CashierReceipt"],
                    MessageReference: {
                        SaleID: this._adyenGetSaleId(),
                        ServiceID: line.uiState.adyenTerminalServiceId,
                        MessageCategory: line.uiState.adyenRefundTransactionId
                            ? "Reversal"
                            : "Payment",
                    },
                },
            },
        };
    }
}

registry.category("pos_payment_providers").add("adyen", PaymentAdyen);
