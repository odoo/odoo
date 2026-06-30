import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { roundPrecision } from "@web/core/utils/numbers";
import { uuidv4 } from "@point_of_sale/utils";
import { registry } from "@web/core/registry";

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
        this.connectWebSocket("VIVA_COM_LATEST_RESPONSE", (payload) => {
            if (payload.config_id === this.pos.config.id) {
                const paymentLine = this.pos.models["pos.payment"].find(
                    (line) => line.viva_com_session_id === payload.session_id
                );

                if (
                    paymentLine &&
                    !paymentLine.isDone() &&
                    paymentLine.getPaymentStatus() !== "retry"
                ) {
                    paymentLine.payment_method_id.payment_terminal.handleVivaComStatusResponse(
                        paymentLine,
                        payload
                    );
                }
            }
        });
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

    getCashRegisterId() {
        return this.pos.getCashier?.().name?.trim() || this.pos.config.name;
    }

    _call_viva_com(data, action, paymentLine) {
        return this.callPaymentMethod(action, [[this.payment_method_id.id], data]).catch(
            this._handleOdooConnectionFailure.bind(this, paymentLine)
        );
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
        paymentLine.setPaymentStatus("waitingCard");
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

        if (order.partner) {
            customerTrns = order.partner.name + " - " + order.partner.email;
        }

        line.viva_com_session_id = order.uuid + " - " + uuidv4();
        const cashRegisterId = this.getCashRegisterId();
        var data = {
            sessionId: line.viva_com_session_id,
            parentSessionId: line.uiState.vivaComParentSessionId,
            terminalId: line.payment_method_id.viva_com_terminal_id,
            cashRegisterId,
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

        return this._call_viva_com(data, action, line).then((data) =>
            this._viva_com_handle_response(data, line)
        );
    }

    async _viva_com_cancel(order, uuid) {
        const line = order.getPaymentlineByUuid(uuid);

        const cashRegisterId = this.getCashRegisterId();
        var data = {
            sessionId: line.viva_com_session_id,
            cashRegisterId,
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
            const sessionId = paymentLine.viva_com_session_id;
            this.paymentLineResolvers[paymentLine.uuid] = resolve;
            let connectionLost = false;
            const intervalId = setInterval(async () => {
                const isPaymentStillValid = () =>
                    this.paymentLineResolvers[paymentLine.uuid] &&
                    sessionId === paymentLine.viva_com_session_id;
                if (!isPaymentStillValid()) {
                    clearInterval(intervalId);
                    return;
                }

                let result;
                try {
                    result = await this.callPaymentMethod("viva_com_get_payment_status", [
                        [this.payment_method_id.id],
                        sessionId,
                    ]);
                } catch {
                    // Connection failure during polling — the payment may have
                    // gone through on Viva's side. Keep polling silently until
                    // we get a definitive answer.
                    if (!connectionLost) {
                        connectionLost = true;
                        this.env.services.notification.add(
                            _t(
                                "No internet connection. Waiting for recovery to confirm the payment..."
                            ),
                            { type: "warning" }
                        );
                    }
                    return;
                }
                connectionLost = false;
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
        line.transaction_id = notification.transactionId;
        line.card_type = notification.cardType;
        line.card_brand = notification.applicationLabel;
        line.card_no = notification.primaryAccountNumberMasked;
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

registry.category("electronic_payment_interfaces").add("viva_com", PaymentVivaCom);
