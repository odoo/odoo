/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { sprintf } from "@web/core/utils/strings";
const { DateTime } = luxon;

export class PaymentAdyen extends PaymentInterface {
    send_payment_request(cid) {
        super.send_payment_request(cid);
        this._reset_state();
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
        return this.pos
            .get_order()
            .paymentlines.find(
                (paymentLine) =>
                    paymentLine.payment_method.use_payment_terminal === "adyen" &&
                    !paymentLine.is_done()
            );
    }

    // private methods
    _reset_state() {
        this.was_cancelled = false;
        this.remaining_polls = 4;
        clearTimeout(this.polling);
    }

    _handle_odoo_connection_failure(data) {
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

    _call_adyen(data, operation) {
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
                            TransactionID: order.uid,
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
        var self = this;
        var order = this.pos.get_order();

        if (order.selected_paymentline.amount < 0) {
            this._show_error(_t("Cannot process transactions with negative amount."));
            return Promise.resolve();
        }

        if (order === this.poll_error_order) {
            delete this.poll_error_order;
            return self._adyen_handle_response({});
        }

        var data = this._adyen_pay_data();
        var line = order.paymentlines.find((paymentLine) => paymentLine.cid === cid);
        line.setTerminalServiceId(this.most_recent_service_id);
        return this._call_adyen(data).then(function (data) {
            return self._adyen_handle_response(data);
        });
    }

    _adyen_cancel(ignore_error) {
        var self = this;
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

        return this._call_adyen(data).then(function (data) {
            // Only valid response is a 200 OK HTTP response which is
            // represented by true.
            if (!ignore_error && data !== true) {
                self._show_error(
                    _t(
                        "Cancelling the payment failed. Please cancel it manually on the payment terminal."
                    )
                );
                self.was_cancelled = !!self.polling;
            }
        });
    }

    _convert_receipt_info(output_text) {
        return output_text.reduce(function (acc, entry) {
            var params = new URLSearchParams(entry.Text);
            if (params.get("name") && !params.get("value")) {
                return acc + sprintf("\n%s", params.get("name"));
            } else if (params.get("name") && params.get("value")) {
                return acc + sprintf("\n%s: %s", params.get("name"), params.get("value"));
            }

            return acc;
        }, "");
    }

    _poll_for_response(resolve, reject) {
        var self = this;
        if (this.was_cancelled) {
            resolve(false);
            return Promise.resolve();
        }

        // FIXME POSREF TIMEOUT 5000
        return this.env.services.orm.silent
            .call("pos.payment.method", "get_latest_adyen_status", [
                [this.payment_method.id],
                this._adyen_get_sale_id(),
            ])
            .catch(function (data) {
                if (self.remaining_polls != 0) {
                    self.remaining_polls--;
                } else {
                    reject();
                    self.poll_error_order = self.pos.get_order();
                    return self._handle_odoo_connection_failure(data);
                }
                // This is to make sure that if 'data' is not an instance of Error (i.e. timeout error),
                // this promise don't resolve -- that is, it doesn't go to the 'then' clause.
                return Promise.reject(data);
            })
            .then(function (status) {
                var notification = status.latest_response;
                var order = self.pos.get_order();
                var line = self.pending_adyen_line() || resolve(false);

                if (
                    notification &&
                    notification.SaleToPOIResponse.MessageHeader.ServiceID == line.terminalServiceId
                ) {
                    var response = notification.SaleToPOIResponse.PaymentResponse.Response;
                    var additional_response = new URLSearchParams(response.AdditionalResponse);

                    if (response.Result == "Success") {
                        var config = self.pos.config;
                        var payment_response = notification.SaleToPOIResponse.PaymentResponse;
                        var payment_result = payment_response.PaymentResult;

                        var cashier_receipt = payment_response.PaymentReceipt.find(function (
                            receipt
                        ) {
                            return receipt.DocumentQualifier == "CashierReceipt";
                        });

                        if (cashier_receipt) {
                            line.set_cashier_receipt(
                                self._convert_receipt_info(cashier_receipt.OutputContent.OutputText)
                            );
                        }

                        var customer_receipt = payment_response.PaymentReceipt.find(function (
                            receipt
                        ) {
                            return receipt.DocumentQualifier == "CustomerReceipt";
                        });

                        if (customer_receipt) {
                            line.set_receipt_info(
                                self._convert_receipt_info(
                                    customer_receipt.OutputContent.OutputText
                                )
                            );
                        }

                        var tip_amount = payment_result.AmountsResp.TipAmount;
                        if (config.adyen_ask_customer_for_tip && tip_amount > 0) {
                            order.set_tip(tip_amount);
                            line.set_amount(payment_result.AmountsResp.AuthorizedAmount);
                        }

                        line.transaction_id = additional_response.get("pspReference");
                        line.card_type = additional_response.get("cardType");
                        line.cardholder_name = additional_response.get("cardHolderName") || "";
                        resolve(true);
                    } else {
                        var message = additional_response.get("message");
                        self._show_error(sprintf(_t("Message from Adyen: %s"), message));

                        // this means the transaction was cancelled by pressing the cancel button on the device
                        if (message.startsWith("108 ")) {
                            resolve(false);
                        } else {
                            line.set_payment_status("retry");
                            reject();
                        }
                    }
                } else {
                    line.set_payment_status("waitingCard");
                }
            });
    }

    _adyen_handle_response(response) {
        var line = this.pending_adyen_line();

        if (response.error && response.error.status_code == 401) {
            this._show_error(_t("Authentication failed. Please check your Adyen credentials."));
            line.set_payment_status("force_done");
            return Promise.resolve();
        }

        response = response.SaleToPOIRequest;
        if (
            response &&
            response.EventNotification &&
            response.EventNotification.EventToNotify == "Reject"
        ) {
            console.error("error from Adyen", response);

            var msg = "";
            if (response.EventNotification) {
                var params = new URLSearchParams(response.EventNotification.EventDetails);
                msg = params.get("message");
            }

            this._show_error(
                sprintf(_t("An unexpected error occurred. Message from Adyen: %s"), msg)
            );
            if (line) {
                line.set_payment_status("force_done");
            }

            return Promise.resolve();
        } else {
            line.set_payment_status("waitingCard");
            return this.start_get_status_polling();
        }
    }

    start_get_status_polling() {
        var self = this;
        var res = new Promise(function (resolve, reject) {
            // clear previous intervals just in case, otherwise
            // it'll run forever
            clearTimeout(self.polling);
            self._poll_for_response(resolve, reject);
            self.polling = setInterval(function () {
                self._poll_for_response(resolve, reject);
            }, 5500);
        });

        // make sure to stop polling when we're done
        res.finally(function () {
            self._reset_state();
        });

        return res;
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
