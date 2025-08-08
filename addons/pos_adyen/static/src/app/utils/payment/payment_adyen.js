import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { register_payment_method } from "@point_of_sale/app/services/pos_store";
import { sprintf } from "@web/core/utils/strings";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";
const { DateTime } = luxon;

export class PaymentAdyen extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.paymentLineResolvers = {};
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
        return this.pos.data
            .silentCall("pos.payment.method", "proxy_adyen_request", [
                [this.payment_method_id.id],
                data,
                operation,
            ])
            .catch(this._handleOdooConnectionFailure.bind(this));
    }

    _adyenGetSaleId() {
        var config = this.pos.config;
        return sprintf("%s (ID: %s)", config.display_name, config.id);
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

    _adyenPay(uuid) {
        var order = this.pos.getOrder();

        if (order.getSelectedPaymentline().amount < 0) {
            this._show_error(_t("Cannot process transactions with negative amount."));
            return Promise.resolve();
        }

        var data = this._adyenPayData();
        var line = order.payment_ids.find((paymentLine) => paymentLine.uuid === uuid);
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
        });
    }

    _convertReceiptInfo(output_text) {
        return output_text.reduce((acc, entry) => {
            var params = new URLSearchParams(entry.Text);
            if (params.get("name") && !params.get("value")) {
                return acc + sprintf("\n%s", params.get("name"));
            } else if (params.get("name") && params.get("value")) {
                return acc + sprintf("\n%s: %s", params.get("name"), params.get("value"));
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

        if (response.error && response.error.status_code == 401) {
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

    waitForPaymentConfirmation() {
        return new Promise((resolve) => {
            this.paymentLineResolvers[this.pendingAdyenline().uuid] = resolve;
        });
    }

    /**
     * This method is called from pos_bus when the payment
     * confirmation from Adyen is received via the webhook.
     */
    async handleAdyenStatusResponse() {
        const notification = await this.pos.data.silentCall(
            "pos.payment.method",
            "get_latest_adyen_status",
            [[this.payment_method_id.id]]
        );

        if (!notification) {
            this._handleOdooConnectionFailure();
            return;
        }
        const line = this.pendingAdyenline();
        const response = notification.SaleToPOIResponse.PaymentResponse.Response;
        const additional_response = new URLSearchParams(response.AdditionalResponse);
        const isPaymentSuccessful = this.isPaymentSuccessful(notification, response);
        if (isPaymentSuccessful) {
            this.handleSuccessResponse(line, notification, additional_response);
        } else {
            this._show_error(
                sprintf(_t("Message from Adyen: %s"), additional_response.get("message"))
            );
        }
        // when starting to wait for the payment response we create a promise
        // that will be resolved when the payment response is received.
        // In case this resolver is lost ( for example on a refresh ) we
        // we use the handlePaymentResponse method on the payment line
        const resolver = this.paymentLineResolvers?.[line?.uuid];
        if (resolver) {
            resolver(isPaymentSuccessful);
        } else {
            line?.handlePaymentResponse(isPaymentSuccessful);
        }
    }
    isPaymentSuccessful(notification, response) {
        return (
            notification &&
            notification.SaleToPOIResponse.MessageHeader.ServiceID ==
                this.pendingAdyenline()?.terminalServiceId &&
            response.Result === "Success"
        );
    }
    handleSuccessResponse(line, notification, additional_response) {
        const config = this.pos.config;
        const payment_response = notification.SaleToPOIResponse.PaymentResponse;
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

        const tip_amount = payment_result.AmountsResp.TipAmount;
        if (config.adyen_ask_customer_for_tip && tip_amount > 0) {
            this.pos.setTip(tip_amount);
            line.setAmount(payment_result.AmountsResp.AuthorizedAmount);
        }

        line.transaction_id = additional_response.get("pspReference");
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

register_payment_method("adyen", PaymentAdyen);
