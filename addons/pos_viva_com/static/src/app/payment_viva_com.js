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
        return this._viva_com_cancel();
    }
    pending_viva_com_line() {
        return this.pos.getPendingPaymentLine("viva_com");
    }

    _call_viva_com(data, action) {
        return this.env.services.orm.silent
            .call("pos.payment.method", action, [[this.payment_method_id.id], data])
            .catch(this._handleOdooConnectionFailure.bind(this));
    }

    _handleOdooConnectionFailure(data = {}) {
        // handle timeout
        var line = this.pending_viva_com_line();
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

    _viva_com_handle_response(response) {
        var line = this.pending_viva_com_line();
        line.setPaymentStatus("waitingCard");
        if (response.error) {
            this._show_error(response.error);
        }
        return this.waitForPaymentConfirmation();
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

        line.viva_com_session_id = order.uuid + " - " + uuidv4();
        var data = {
            sessionId: line.viva_com_session_id,
            parentSessionId: line.uiState.vivaComParentSessionId,
            terminalId: line.payment_method_id.viva_com_terminal_id,
            cashRegisterId: this.pos.getCashier().name,
            amount: roundPrecision(Math.abs(line.amount * 100)),
            currencyCode: this.pos.currency.iso_numeric.toString(),
            merchantReference: line.viva_com_session_id + "/" + this.pos.session.id,
            customerTrns: customerTrns,
            preauth: false,
            maxInstalments: 0,
            tipAmount: 0,
        };

        const action =
            line.amount < 0 ? "viva_com_send_refund_request" : "viva_com_send_payment_request";

        return this._call_viva_com(data, action).then((data) =>
            this._viva_com_handle_response(data)
        );
    }

    async _viva_com_cancel(order, uuid) {
        /**
         * Override
         */
        super.sendPaymentCancel(...arguments);
        const line = this.pos.getOrder().getSelectedPaymentline();

        var data = {
            sessionId: line.viva_com_session_id,
            cashRegisterId: this.pos.getCashier().name,
        };
        return this._call_viva_com(data, "viva_com_send_payment_cancel").then((data) => {
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
    async handleVivaComStatusResponse() {
        var line = this.pending_viva_com_line();
        const notification = await this.env.services.orm.silent.call(
            "pos.payment.method",
            "get_latest_viva_com_status",
            [[this.payment_method_id.id]]
        );

        if (!notification) {
            this._handleOdooConnectionFailure();
            return;
        }

        const isPaymentSuccessful = this.isPaymentSuccessful(notification);
        if (isPaymentSuccessful) {
            this.handleSuccessResponse(line, notification);
        } else {
            this._show_error(_t("Message from Viva.com: %s", notification.error));
        }

        // when starting to wait for the payment response we create a promise
        // that will be resolved when the payment response is received.
        // In case this resolver is lost ( for example on a refresh )
        // we use the handlePaymentResponse method on the payment line
        const resolver = this.paymentLineResolvers?.[line.uuid];
        if (resolver) {
            this.paymentLineResolvers[line.uuid] = null;
            resolver(isPaymentSuccessful);
        } else {
            line.handlePaymentResponse(isPaymentSuccessful);
        }
    }

    isPaymentSuccessful(notification) {
        return (
            notification &&
            notification.sessionId == this.pending_viva_com_line().viva_com_session_id &&
            notification.success
        );
    }

    waitForPaymentConfirmation() {
        return new Promise((resolve) => {
            const paymentLine = this.pending_viva_com_line();
            const sessionId = paymentLine.viva_com_session_id;
            this.paymentLineResolvers[paymentLine.uuid] = resolve;
            const intervalId = setInterval(async () => {
                const isPaymentStillValid = () =>
                    this.paymentLineResolvers[paymentLine.uuid] &&
                    this.pending_viva_com_line()?.viva_com_session_id === sessionId &&
                    paymentLine.payment_status === "waitingCard";
                if (!isPaymentStillValid()) {
                    clearInterval(intervalId);
                    return;
                }

                const result = await this._call_viva_com(sessionId, "viva_com_get_payment_status");
                if ("success" in result && isPaymentStillValid()) {
                    clearInterval(intervalId);
                    if (this.isPaymentSuccessful(result)) {
                        this.handleSuccessResponse(paymentLine, result);
                        resolve(true);
                    } else {
                        resolve(false);
                    }
                    this.paymentLineResolvers[paymentLine.uuid] = null;
                }
            }, POLLING_INTERVAL_MS);
        });
    }

    handleSuccessResponse(line, notification) {
        line.transaction_id = notification.transactionId;
        line.card_type = notification.applicationLabel;
        line.cardholder_name = notification.FullName || "";
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
