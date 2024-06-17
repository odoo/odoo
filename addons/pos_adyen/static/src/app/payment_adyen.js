import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import { sprintf } from "@web/core/utils/strings";

export class PaymentAdyen extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.paymentLineResolvers = {};
    }

    send_payment_request(uuid) {
        super.send_payment_request(uuid);
        return (
            this.pos.data
                .silentCall("pos.payment.method", "send_payment_request", [
                    [this.payment_method_id.id],
                    this.pos
                        .get_order()
                        .payment_ids.find((paymentLine) => paymentLine.uuid === uuid).id,
                ])
                // TODO: figure out how to handle the errors
                .catch(this._handle_odoo_connection_failure.bind(this))
                .then((data) => {
                    const line = this.pending_adyen_line();
                    line.set_payment_status(data.payment_status);
                })
        );
    }
    send_payment_cancel(order, uuid) {
        super.send_payment_cancel(order, uuid);
        var config = this.pos.config;
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
                        // ServiceID: previous_service_id,
                    },
                },
            },
        };

        return this._call_adyen(data).then((data) => {
            // Only valid response is a 200 OK HTTP response which is
            // represented by true.
            if (data !== true) {
                this._show_error(
                    _t(
                        "Cancelling the payment failed. Please cancel it manually on the payment terminal."
                    )
                );
            }
        });
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

    _adyen_get_sale_id() {
        var config = this.pos.config;
        return sprintf("%s (ID: %s)", config.display_name, config.id);
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

    waitForPaymentConfirmation() {
        return new Promise((resolve) => {
            this.paymentLineResolvers[this.pending_adyen_line().uuid] = resolve;
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
        const resolver = this.paymentLineResolvers?.[line.uuid];
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
        const payment_response = notification.SaleToPOIResponse.PaymentResponse;
        const payment_result = payment_response.PaymentResult;

        const cashier_receipt = payment_response.PaymentReceipt.find((receipt) => {
            return receipt.DocumentQualifier == "CashierReceipt";
        });

        if (cashier_receipt) {
            line.set_cashier_receipt(
                this._convert_receipt_info(cashier_receipt.OutputContent.OutputText)
            );
        }

        const customer_receipt = payment_response.PaymentReceipt.find((receipt) => {
            return receipt.DocumentQualifier == "CustomerReceipt";
        });

        if (customer_receipt) {
            line.set_receipt_info(
                this._convert_receipt_info(customer_receipt.OutputContent.OutputText)
            );
        }

        const tip_amount = payment_result.AmountsResp.TipAmount;
        if (config.adyen_ask_customer_for_tip && tip_amount > 0) {
            this.pos.set_tip(tip_amount);
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
        this.env.services.dialog.add(AlertDialog, {
            title: title,
            body: msg,
        });
    }
}

register_payment_method("adyen", PaymentAdyen);
