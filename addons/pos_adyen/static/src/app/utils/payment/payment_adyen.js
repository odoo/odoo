import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";
const { DateTime } = luxon;

const POLLING_INTERVAL_MS = 5000;

export class PaymentAdyen extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.paymentLineResolvers = {};
        this.connectWebSocket("ADYEN_LATEST_RESPONSE", () => {
            const pendingLine = this.pos.getPendingPaymentLine("adyen");

            if (pendingLine) {
                pendingLine.payment_method_id.payment_terminal.handleAdyenStatusResponse();
            }
        });
    }

    sendPaymentRequest(uuid) {
        super.sendPaymentRequest(uuid);
        return this._adyenPay(uuid);
    }
    sendPaymentCancel(order, uuid) {
        super.sendPaymentCancel(order, uuid);
        return this._adyenCancel();
    }

    setMostRecentServiceId(id) {
        this.most_recent_service_id = id;
    }

    pendingAdyenline() {
        return this.pos.getPendingPaymentLine("adyen");
    }

    sendPaymentAdjust(uuid) {
        var order = this.pos.getOrder();
        var line = order.getPaymentlineByUuid(uuid);
        var data = {
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

        return this._callAdyen(data, "adjust");
    }

    canBeAdjusted(uuid) {
        var order = this.pos.getOrder();
        var line = order.getPaymentlineByUuid(uuid);
        return ["mc", "visa", "amex", "discover"].includes(line.card_type);
    }

    _handleOdooConnectionFailure(data = {}) {
        // handle timeout
        var line = this.pendingAdyenline();
        if (line) {
            line.setPaymentStatus("retry");
        }
        this._show_error(
            _t(
                "Could not connect to the Odoo server, please check your internet connection and try again."
            )
        );

        return Promise.reject(data); // prevent subsequent onFullFilled's from being called
    }

    _callAdyen(data, operation = false) {
        return this.callPaymentMethod("proxy_adyen_request", [
            [this.payment_method_id.id],
            data,
            operation,
        ]).catch(this._handleOdooConnectionFailure.bind(this));
    }

    _adyenGetSaleId() {
        var config = this.pos.config;
        return `${config.display_name} (ID: ${config.id})`;
    }

    _adyenCommonMessageHeader() {
        var config = this.pos.config;
        this.most_recent_service_id = Math.floor(Math.random() * Math.pow(2, 64)).toString(); // random ID to identify request/response pairs
        this.most_recent_service_id = this.most_recent_service_id.substring(0, 10); // max length is 10

        return {
            ProtocolVersion: "3.0",
            MessageClass: "Service",
            MessageType: "Request",
            SaleID: this._adyenGetSaleId(config),
            ServiceID: this.most_recent_service_id,
            POIID: this.payment_method_id.adyen_terminal_identifier,
        };
    }

    _adyenPayData() {
        var order = this.pos.getOrder();
        var config = this.pos.config;
        var line = order.getSelectedPaymentline();
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

        if (config.adyen_ask_customer_for_tip) {
            data.SaleToPOIRequest.PaymentRequest.SaleData.SaleToAcquirerData =
                "tenderOption=AskGratuity";
        }

        return data;
    }

    _adyenReversalData() {
        const order = this.pos.getOrder();
        const line = order.getSelectedPaymentline();
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

    _adyenPay(uuid) {
        const order = this.pos.getOrder();
        const line = order.payment_ids.find((paymentLine) => paymentLine.uuid === uuid);

        if (line.amount < 0 && !line.uiState.adyenRefundTransactionId) {
            this._show_error(_t("Cannot refund non-Adyen transactions via Adyen."));
            return false;
        }

        const data = line.amount < 0 ? this._adyenReversalData() : this._adyenPayData();
        line.setTerminalServiceId(this.most_recent_service_id);
        return this._callAdyen(data).then((data) => this._adyenHandleResponse(data));
    }

    _adyenCancel(ignore_error) {
        var config = this.pos.config;
        var previous_service_id = this.most_recent_service_id;
        var header = Object.assign(this._adyenCommonMessageHeader(), {
            MessageCategory: "Abort",
        });

        var data = {
            SaleToPOIRequest: {
                MessageHeader: header,
                AbortRequest: {
                    AbortReason: "MerchantAbort",
                    MessageReference: {
                        MessageCategory: "Payment",
                        SaleID: this._adyenGetSaleId(config),
                        ServiceID: previous_service_id,
                    },
                },
            },
        };

        return this._callAdyen(data).then((data) => {
            // Only valid response is a 200 OK HTTP response which is
            // represented by true.
            if (!ignore_error && data !== true) {
                this._show_error(
                    _t(
                        "Cancelling the payment failed. Please cancel it manually on the payment terminal."
                    )
                );
            }
            return true;
        });
    }

    _adyenCheckPaymentStatus(paymentServiceId, isRefund) {
        const data = {
            SaleToPOIRequest: {
                MessageHeader: Object.assign(this._adyenCommonMessageHeader(), {
                    MessageCategory: "TransactionStatus",
                }),
                TransactionStatusRequest: {
                    ReceiptReprintFlag: true,
                    DocumentQualifier: ["CustomerReceipt", "CashierReceipt"],
                    MessageReference: {
                        SaleID: this._adyenGetSaleId(),
                        ServiceID: paymentServiceId,
                        MessageCategory: isRefund ? "Reversal" : "Payment",
                    },
                },
            },
        };

        return this._callAdyen(data, "payment_status");
    }

    _convertReceiptInfo(output_text) {
        return output_text.reduce((acc, entry) => {
            var params = new URLSearchParams(entry.Text);
            if (params.get("name") && !params.get("value")) {
                return acc + "\n" + params.get("name");
            } else if (params.get("name") && params.get("value")) {
                return `${acc}\n${params.get("name")}: ${params.get("value")}`;
            }

            return acc;
        }, "");
    }

    /**
     * This method handles the response that comes from Adyen
     * when we first make a request to pay.
     */
    _adyenHandleResponse(response) {
        var line = this.pendingAdyenline();

        if (!response || (response.error && response.error.status_code == 401)) {
            this._show_error(_t("Authentication failed. Please check your Adyen credentials."));
            line.setPaymentStatus("force_done");
            return false;
        }

        response = response.SaleToPOIRequest;
        if (response?.EventNotification?.EventToNotify === "Reject") {
            logPosMessage("PaymentAdyen", "_adyenHandleResponse", `Error from Adyen`, false, [
                response,
            ]);

            var msg = "";
            if (response.EventNotification) {
                var params = new URLSearchParams(response.EventNotification.EventDetails);
                msg = params.get("message");
            }

            this._show_error(_t("An unexpected error occurred. Message from Adyen: %s", msg));
            if (line) {
                line.setPaymentStatus("force_done");
            }
            return false;
        } else {
            line.setPaymentStatus("waitingCard");
            return this.waitForPaymentConfirmation();
        }
    }

    _adyenHandlePaymentStatus(response, paymentLine, resolve, pollingIntervalId) {
        const transactionStatus = response.SaleToPOIResponse.TransactionStatusResponse.Response;

        if (transactionStatus.Result === "Success") {
            clearInterval(pollingIntervalId);
            const repeatedResponseMessage =
                response.SaleToPOIResponse.TransactionStatusResponse.RepeatedMessageResponse;
            const body = repeatedResponseMessage.RepeatedResponseMessageBody;
            const header = repeatedResponseMessage.MessageHeader;
            this.processPaymentResponse(paymentLine, header, body);
        } else if (transactionStatus.ErrorCondition === "NotFound") {
            clearInterval(pollingIntervalId);
            resolve(false);
        }
    }

    waitForPaymentConfirmation() {
        return new Promise((resolve) => {
            const paymentLine = this.pendingAdyenline();
            const serviceId = paymentLine.terminalServiceId;
            this.paymentLineResolvers[paymentLine.uuid] = resolve;

            const intervalId = setInterval(async () => {
                const isPaymentStillValid = () =>
                    this.paymentLineResolvers[paymentLine.uuid] &&
                    this.pendingAdyenline()?.terminalServiceId === serviceId &&
                    paymentLine.payment_status === "waitingCard";

                if (!isPaymentStillValid()) {
                    clearInterval(intervalId);
                    return;
                }

                const response = await this._adyenCheckPaymentStatus(
                    serviceId,
                    !!paymentLine.uiState.adyenRefundTransactionId
                );
                if (response && isPaymentStillValid()) {
                    this._adyenHandlePaymentStatus(response, paymentLine, resolve, intervalId);
                }
            }, POLLING_INTERVAL_MS);
        });
    }

    processPaymentResponse(line, header, body) {
        const paymentResponse = body.PaymentResponse ?? body.ReversalResponse;
        const additionalResponse = new URLSearchParams(paymentResponse.Response.AdditionalResponse);
        const isPaymentSuccessful = this.isPaymentSuccessful(header, paymentResponse.Response);
        if (isPaymentSuccessful) {
            this.handleSuccessResponse(line, paymentResponse, additionalResponse);
        } else {
            this._show_error(_t("Message from Adyen: %s", additionalResponse.get("message")));
        }
        // when starting to wait for the payment response we create a promise
        // that will be resolved when the payment response is received.
        // In case this resolver is lost ( for example on a refresh ) we
        // we use the handle_payment_response method on the payment line
        const resolver = this.paymentLineResolvers?.[line.uuid];
        if (resolver) {
            this.paymentLineResolvers[line.uuid] = null;
            resolver(isPaymentSuccessful);
        } else {
            line.handlePaymentResponse(isPaymentSuccessful);
        }
    }

    /**
     * This method is called from pos_bus when the payment
     * confirmation from Adyen is received via the webhook.
     */
    async handleAdyenStatusResponse() {
        const notification = await this.callPaymentMethod("get_latest_adyen_status", [
            [this.payment_method_id.id],
        ]);

        if (!notification) {
            this._handleOdooConnectionFailure();
            return;
        }
        const line = this.pendingAdyenline();
        const response = notification.SaleToPOIResponse;
        const header = notification.SaleToPOIResponse.MessageHeader;

        this.processPaymentResponse(line, header, response);
    }
    isPaymentSuccessful(header, response) {
        return (
            header.ServiceID === this.pendingAdyenline().terminalServiceId &&
            response.Result === "Success"
        );
    }
    handleSuccessResponse(line, payment_response, additional_response) {
        const config = this.pos.config;
        const payment_result = payment_response.PaymentResult;

        const cashier_receipt = payment_response.PaymentReceipt.find(
            (receipt) => receipt.DocumentQualifier == "CashierReceipt"
        );

        if (cashier_receipt) {
            line.setCashierReceipt(
                this._convertReceiptInfo(cashier_receipt.OutputContent.OutputText)
            );
        }

        const customer_receipt = payment_response.PaymentReceipt.find(
            (receipt) => receipt.DocumentQualifier == "CustomerReceipt"
        );

        if (customer_receipt) {
            line.setReceiptInfo(
                this._convertReceiptInfo(customer_receipt.OutputContent.OutputText)
            );
        }

        const tip_amount = payment_result?.AmountsResp?.TipAmount ?? 0;
        if (config.adyen_ask_customer_for_tip && tip_amount > 0) {
            this.pos.setTip(tip_amount);
            line.setAmount(payment_result.AmountsResp.AuthorizedAmount);
        }

        line.transaction_id = payment_response.POIData.POITransactionID.TransactionID;
        line.card_type = additional_response.get("cardType");
        line.cardholder_name = additional_response.get("cardHolderName") || "";
    }

    _show_error(msg, title) {
        if (!title) {
            title = _t("Adyen Error");
        }
        this.env.services.dialog.add(AlertDialog, {
            title: title,
            body: msg,
        });
    }
}

registry.category("electronic_payment_interfaces").add("adyen", PaymentAdyen);
