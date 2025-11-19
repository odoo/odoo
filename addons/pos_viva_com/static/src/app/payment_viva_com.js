import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { roundPrecision } from "@web/core/utils/numbers";
import { uuidv4 } from "@point_of_sale/utils";
import { register_payment_method } from "@point_of_sale/app/services/pos_store";

// Due to consistency issues with the webhook, we also poll
// the status of the payment periodically as a fallback.
const POLLING_INTERVAL_MS = 5000;

export class PaymentVivaCom extends PaymentInterface {
    /*
     Developer documentation:
    https://developer.viva.com/apis-for-point-of-sale/card-terminals-devices/rest-api/eft-pos-api-documentation/
    */

    setup() {
        super.setup(...arguments);
        this.paymentLineResolvers = {};
    }
    sendPaymentRequest(uuid) {
        super.sendPaymentRequest(uuid);
        return this._viva_com_pay(uuid);
    }
    sendPaymentCancel(order, uuid) {
        super.sendPaymentCancel(order, uuid);
        return this._viva_com_cancel(order, uuid);
    }

    _call_viva_com(data, action, paymentLine) {
        return this.env.services.orm.silent
            .call("pos.payment.method", action, [[this.payment_method_id.id], data])
            .catch(this._handleOdooConnectionFailure.bind(this, paymentLine));
    }

    _handleOdooConnectionFailure(paymentLine, data = {}) {
        // handle timeout
        if (!paymentLine.isDone()) {
            paymentLine.setPaymentStatus("retry");
        }
        this._show_error(
            _t(
                "Could not connect to the Odoo server, please check your internet connection and try again."
            )
        );

        return Promise.reject(data); // prevent subsequent onFullFilled's from being called
    }

    _viva_com_handle_response(response, paymentLine) {
        if (response.error) {
            this._show_error(response.error);
            return false;
        }
        return this.waitForPaymentConfirmation(paymentLine);
    }

    _viva_com_pay() {
        /**
         * Override
         */
        super.sendPaymentRequest(...arguments);
        var order = this.pos.getOrder();
        var line = order.getSelectedPaymentline();
        let customerTrns = " ";
        line.setPaymentStatus("waitingCard");

        if (order.partner) {
            customerTrns = order.partner.name + " - " + order.partner.email;
        }

        line.uiState.vivaSessionId = order.uuid + " - " + uuidv4();
        var data = {
            sessionId: line.uiState.vivaSessionId,
            terminalId: line.payment_method_id.viva_com_terminal_id,
            cashRegisterId: this.pos.getCashier().name,
            amount: roundPrecision(Math.abs(line.amount * 100)),
            currencyCode: this.pos.currency.iso_numeric.toString(),
            merchantReference: line.uiState.vivaSessionId + "/" + this.pos.session.id,
            customerTrns: customerTrns,
            preauth: false,
            maxInstalments: 0,
            tipAmount: 0,
        };

        const action =
            line.amount < 0 ? "viva_com_send_refund_request" : "viva_com_send_payment_request";

        return this._call_viva_com(data, action, line).then((data) =>
            this._viva_com_handle_response(data, line)
        );
    }

    async _viva_com_cancel(order, uuid) {
        const line = order.getPaymentlineByUuid(uuid);

        var data = {
            sessionId: line.uiState.vivaSessionId,
            cashRegisterId: this.pos.getCashier().name,
        };
        return this._call_viva_com(data, "viva_com_send_payment_cancel", line).then((data) => {
            if (data.error) {
                this._show_error(data.error);
            }
            return true;
        });
    }

    /**
     * This method is called from pos_bus when the payment
     * confirmation from Viva.com is received via the webhook and confirmed in the retrieve_session_id.
     */
    handleVivaComStatusResponse(paymentLine, notification) {
        if (!notification) {
            this._handleOdooConnectionFailure(paymentLine);
            return;
        }

        const isPaymentSuccessful = this.isPaymentSuccessful(notification);
        if (isPaymentSuccessful) {
            this.handleSuccessResponse(paymentLine, notification);
        } else {
            this._show_error(_t("Message from Viva.com: %s", notification.error));
        }

        // when starting to wait for the payment response we create a promise
        // that will be resolved when the payment response is received.
        // In case this resolver is lost ( for example on a refresh )
        // we use the handlePaymentResponse method on the payment line
        const resolver = this.paymentLineResolvers?.[paymentLine.uuid];
        if (resolver) {
            this.paymentLineResolvers[paymentLine.uuid] = null;
            resolver(isPaymentSuccessful);
        } else {
            paymentLine.handlePaymentResponse(isPaymentSuccessful);
        }
    }

    isPaymentSuccessful(notification) {
        return notification && notification.success;
    }

    waitForPaymentConfirmation(paymentLine) {
        return new Promise((resolve) => {
            const sessionId = paymentLine.uiState.vivaSessionId;
            this.paymentLineResolvers[paymentLine.uuid] = resolve;
            const intervalId = setInterval(async () => {
                const isPaymentStillValid = () =>
                    this.paymentLineResolvers[paymentLine.uuid] &&
                    paymentLine.payment_status === "waitingCard" &&
                    sessionId === paymentLine.uiState.vivaSessionId;
                if (!isPaymentStillValid()) {
                    clearInterval(intervalId);
                    return;
                }

                const result = await this._call_viva_com(
                    sessionId,
                    "viva_com_get_payment_status",
                    paymentLine
                );
                if ("success" in result && isPaymentStillValid()) {
                    clearInterval(intervalId);
                    if (this.isPaymentSuccessful(result)) {
                        this.handleSuccessResponse(paymentLine, result);
                        resolve(true);
                    } else {
                        this._show_error(_t("Message from Viva.com: %s", result.message));
                        resolve(false);
                    }
                    this.paymentLineResolvers[paymentLine.uuid] = null;
                }
            }, POLLING_INTERVAL_MS);
        });
    }

    handleSuccessResponse(line, notification) {
        line.transaction_id = notification.transaction_id;
        line.card_type = notification.card_type;
        line.cardholder_name = notification.cardholder_name;
    }

    _show_error(msg, title) {
        if (!title) {
            title = _t("Viva.com Error");
        }
        this.env.services.dialog.add(AlertDialog, {
            title: title,
            body: msg,
        });
    }
}

register_payment_method("viva_com", PaymentVivaCom);
