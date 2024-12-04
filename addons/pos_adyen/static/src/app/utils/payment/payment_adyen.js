import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { register_payment_method } from "@point_of_sale/app/services/pos_store";
import { sprintf } from "@web/core/utils/strings";

export class PaymentAdyen extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.paymentLineResolvers = {};
    }

    sendPaymentRequest(uuid) {
        super.sendPaymentRequest(uuid);
        return (
            this.pos.data
                .silentCall("pos.payment.method", "send_payment_request", [
                    [this.payment_method_id.id],
                    this.pos.getOrder().payment_ids.find((paymentLine) => paymentLine.uuid === uuid)
                        .id,
                ])
                // TODO: figure out how to handle the errors
                .catch(this._handleOdooConnectionFailure.bind(this))
                .then((data) => {
                    const line = this.pendingAdyenline();
                    line.setPaymentStatus(data.payment_status);
                })
        );
    }
    sendPaymentCancel(order, uuid) {
        //TODO: implement
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

    _adyen_get_sale_id() {
        var config = this.pos.config;
        return sprintf("%s (ID: %s)", config.display_name, config.id);
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
        const resolver = this.paymentLineResolvers?.[line.uuid];
        if (resolver) {
            resolver(isPaymentSuccessful);
        } else {
            line.handlePaymentResponse(isPaymentSuccessful);
        }
    }
    isPaymentSuccessful(notification, response) {
        return (
            notification &&
            notification.SaleToPOIResponse.MessageHeader.ServiceID ==
                this.pendingAdyenline().terminalServiceId &&
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
            line.setCashierReceipt(
                this._convertReceiptInfo(cashier_receipt.OutputContent.OutputText)
            );
        }

        const customer_receipt = payment_response.PaymentReceipt.find((receipt) => {
            return receipt.DocumentQualifier == "CustomerReceipt";
        });

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
