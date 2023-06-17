/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { sprintf } from "@web/core/utils/strings";
const { DateTime } = luxon;

export class PaymentAdyen extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.paymentLineResolvers = {};
    }

    send_payment_request(cid) {
        super.send_payment_request(cid);
        return this._adyen_pay(cid);
    }
    send_payment_cancel(order, cid) {
        super.send_payment_cancel(order, cid);
        return this._adyen_cancel();
    }

    set_most_recent_service_id(id) {
        this.most_recent_service_id = id;
    }

    pending_adyen_line() {
        return this.pos.getPendingPaymentLine("adyen");
    }

    _handle_odoo_connection_failure(data = {}) {
        // handle timeout
        var line = this.pending_adyen_line();
        if (line) {
            line.set_payment_status("retry");
        }
        this._show_error(
            _t(
                "Could not connect to the Odoo server, please check your internet connection and try again."
            )
        );

        return Promise.reject(data); // prevent subsequent onFullFilled's from being called
    }

    _call_adyen(data, operation = false) {
        // FIXME POSREF TIMEOUT 10000
        return this.env.services.orm.silent
            .call("pos.payment.method", "proxy_adyen_request", [
                [this.payment_method.id],
                data,
                operation,
            ])
            .catch(this._handle_odoo_connection_failure.bind(this));
    }

    _adyen_get_sale_id() {
        var config = this.pos.config;
        return sprintf("%s (ID: %s)", config.display_name, config.id);
    }

    _adyen_common_message_header() {
        var config = this.pos.config;
        this.most_recent_service_id = Math.floor(Math.random() * Math.pow(2, 64)).toString(); // random ID to identify request/response pairs
        this.most_recent_service_id = this.most_recent_service_id.substring(0, 10); // max length is 10

        return {
            ProtocolVersion: "3.0",
            MessageClass: "Service",
            MessageType: "Request",
            SaleID: this._adyen_get_sale_id(config),
            ServiceID: this.most_recent_service_id,
            POIID: this.payment_method.adyen_terminal_identifier,
        };
    }

    _adyen_pay_data() {
        var order = this.pos.get_order();
        var config = this.pos.config;
        var line = order.selected_paymentline;
        var data = {
            SaleToPOIRequest: {
                MessageHeader: Object.assign(this._adyen_common_message_header(), {
                    MessageCategory: "Payment",
                }),
                PaymentRequest: {
                    SaleData: {
                        SaleTransactionID: {
                            TransactionID: `${order.uid}--${order.pos_session_id}`,
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

    _adyen_pay(cid) {
        var order = this.pos.get_order();

        if (order.selected_paymentline.amount < 0) {
            this._show_error(_t("Cannot process transactions with negative amount."));
            return Promise.resolve();
        }

        var data = this._adyen_pay_data();
        var line = order.paymentlines.find((paymentLine) => paymentLine.cid === cid);
        line.setTerminalServiceId(this.most_recent_service_id);
        return this._call_adyen(data).then((data) => {
            return this._adyen_handle_response(data);
        });
    }

    _adyen_cancel(ignore_error) {
        var config = this.pos.config;
        var previous_service_id = this.most_recent_service_id;
        var header = Object.assign(this._adyen_common_message_header(), {
            MessageCategory: "Abort",
        });

        var data = {
            SaleToPOIRequest: {
                MessageHeader: header,
                AbortRequest: {
                    AbortReason: "MerchantAbort",
                    MessageReference: {
                        MessageCategory: "Payment",
                        SaleID: this._adyen_get_sale_id(config),
                        ServiceID: previous_service_id,
                    },
                },
            },
        };

        return this._call_adyen(data).then((data) => {
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

    _convert_receipt_info(output_text) {
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
    _adyen_handle_response(response) {
        var line = this.pending_adyen_line();

        if (response.error && response.error.status_code == 401) {
            this._show_error(_t("Authentication failed. Please check your Adyen credentials."));
            line.set_payment_status("force_done");
            return false;
        }

        response = response.SaleToPOIRequest;
        if (response?.EventNotification?.EventToNotify === "Reject") {
            console.error("error from Adyen", response);

            var msg = "";
            if (response.EventNotification) {
                var params = new URLSearchParams(response.EventNotification.EventDetails);
                msg = params.get("message");
            }

            this._show_error(_t("An unexpected error occurred. Message from Adyen: %s", msg));
            if (line) {
                line.set_payment_status("force_done");
            }
            return false;
        } else {
            line.set_payment_status("waitingCard");
            return this.waitForPaymentConfirmation();
        }
    }

    waitForPaymentConfirmation() {
        return new Promise((resolve) => {
            this.paymentLineResolvers[this.pending_adyen_line().cid] = resolve;
        });
    }

    /**
     * This method is called from pos_bus when the payment
     * confirmation from Adyen is received via the webhook.
     */
    async handleAdyenStatusResponse() {
        const notification = await this.env.services.orm.silent.call(
            "pos.payment.method",
            "get_latest_adyen_status",
            [[this.payment_method.id]]
        );

        if (!notification) {
            this._handle_odoo_connection_failure();
            return;
        }
        const line = this.pending_adyen_line();
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
        // we use the handle_payment_response method on the payment line
        const resolver = this.paymentLineResolvers?.[line.cid];
        if (resolver) {
            resolver(isPaymentSuccessful);
        } else {
            line.handle_payment_response(isPaymentSuccessful);
        }
    }
    isPaymentSuccessful(notification, response) {
        return (
            notification &&
            notification.SaleToPOIResponse.MessageHeader.ServiceID ==
                this.pending_adyen_line().terminalServiceId &&
            response.Result === "Success"
        );
    }
    handleSuccessResponse(line, notification, additional_response) {
        const config = this.pos.config;
        const order = this.pos.get_order();
        const payment_response = notification.SaleToPOIResponse.PaymentResponse;
        const payment_result = payment_response.PaymentResult;

        const cashier_receipt = payment_response.PaymentReceipt.find((receipt) => {
            receipt.DocumentQualifier == "CashierReceipt";
        });

        if (cashier_receipt) {
            line.set_cashier_receipt(
                this._convert_receipt_info(cashier_receipt.OutputContent.OutputText)
            );
        }

        const customer_receipt = payment_response.PaymentReceipt.find((receipt) => {
            receipt.DocumentQualifier == "CustomerReceipt";
        });

        if (customer_receipt) {
            line.set_receipt_info(
                this._convert_receipt_info(customer_receipt.OutputContent.OutputText)
            );
        }

        const tip_amount = payment_result.AmountsResp.TipAmount;
        if (config.adyen_ask_customer_for_tip && tip_amount > 0) {
            order.set_tip(tip_amount);
            line.set_amount(payment_result.AmountsResp.AuthorizedAmount);
        }

        line.transaction_id = additional_response.get("pspReference");
        line.card_type = additional_response.get("cardType");
        line.cardholder_name = additional_response.get("cardHolderName") || "";
    }

    _show_error(msg, title) {
        if (!title) {
            title = _t("Adyen Error");
        }
        this.env.services.popup.add(ErrorPopup, {
            title: title,
            body: msg,
        });
    }
}
