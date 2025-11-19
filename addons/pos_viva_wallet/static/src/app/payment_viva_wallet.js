import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { sprintf } from "@web/core/utils/strings";
import { roundPrecision } from "@web/core/utils/numbers";
import { uuidv4 } from "@point_of_sale/utils";

// Due to consistency issues with the webhook, we also poll
// the status of the payment periodically as a fallback.
const POLLING_INTERVAL_MS = 5000;

export class PaymentVivaWallet extends PaymentInterface {
    /*
     Developer documentation:
    https://developer.vivawallet.com/apis-for-point-of-sale/card-terminals-devices/rest-api/eft-pos-api-documentation/
    */

    setup() {
        super.setup(...arguments);
        this.paymentLineResolvers = {};
    }
    send_payment_request(uuid) {
        super.send_payment_request(uuid);
        return this._viva_wallet_pay(uuid);
    }
    send_payment_cancel(order, uuid) {
        super.send_payment_cancel(order, uuid);
        return this._viva_wallet_cancel(order, uuid);
    }

    _call_viva_wallet(data, action, paymentLine) {
        return this.env.services.orm.silent
            .call("pos.payment.method", action, [[this.payment_method_id.id], data])
            .catch(this._handle_odoo_connection_failure.bind(this, paymentLine));
    }

    _handle_odoo_connection_failure(paymentLine, data = {}) {
        // handle timeout
        if (!paymentLine.is_done()) {
            paymentLine.set_payment_status("retry");
        }
        this._show_error(
            _t(
                "Could not connect to the Odoo server, please check your internet connection and try again."
            )
        );

        return Promise.reject(data); // prevent subsequent onFullFilled's from being called
    }

    _viva_wallet_handle_response(response, paymentLine) {
        if (response.error) {
            this._show_error(response.error);
            return false;
        }
        return this.waitForPaymentConfirmation(paymentLine);
    }

    _viva_wallet_pay() {
        /**
         * Override
         */
        super.send_payment_request(...arguments);
        var order = this.pos.get_order();
        var line = order.get_selected_paymentline();
        let customerTrns = " ";
        line.set_payment_status("waitingCard");

        if (line.amount < 0) {
            this._show_error(_t("Cannot process transactions with negative amount."));
            return false;
        }

        if (order.partner) {
            customerTrns = order.partner.name + " - " + order.partner.email;
        }

        line.uiState.vivaSessionId = order.uuid + " - " + uuidv4();
        var data = {
            sessionId: line.uiState.vivaSessionId,
            terminalId: line.payment_method_id.viva_wallet_terminal_id,
            cashRegisterId: this.pos.get_cashier().name,
            amount: roundPrecision(line.amount * 100),
            currencyCode: this.pos.currency.iso_numeric.toString(),
            merchantReference: line.uiState.vivaSessionId + "/" + this.pos.session.id,
            customerTrns: customerTrns,
            preauth: false,
            maxInstalments: 0,
            tipAmount: 0,
        };
        return this._call_viva_wallet(data, "viva_wallet_send_payment_request", line).then(
            (data) => {
                return this._viva_wallet_handle_response(data, line);
            }
        );
    }

    async _viva_wallet_cancel(order, uuid) {
        /**
         * Override
         */
        super.send_payment_cancel(...arguments);
        const line = order.get_paymentline_by_uuid(uuid);

        var data = {
            sessionId: line.uiState.vivaSessionId,
            cashRegisterId: this.pos.get_cashier().name,
        };
        return this._call_viva_wallet(data, "viva_wallet_send_payment_cancel", line).then(
            (data) => {
                if (data.error) {
                    this._show_error(data.error);
                }
                return true;
            }
        );
    }

    /**
     * This method is called from pos_bus when the payment
     * confirmation from Viva Wallet is received via the webhook and confirmed in the retrieve_session_id.
     */
    handleVivaWalletStatusResponse(paymentLine, notification) {
        if (!notification) {
            this._handle_odoo_connection_failure(paymentLine);
            return;
        }

        const isPaymentSuccessful = this.isPaymentSuccessful(notification);
        if (isPaymentSuccessful) {
            this.handleSuccessResponse(paymentLine, notification);
        } else {
            this._show_error(sprintf(_t("Message from Viva Wallet: %s"), notification.error));
        }

        // when starting to wait for the payment response we create a promise
        // that will be resolved when the payment response is received.
        // In case this resolver is lost ( for example on a refresh ) we
        // we use the handle_payment_response method on the payment line
        const resolver = this.paymentLineResolvers?.[paymentLine.uuid];
        if (resolver) {
            this.paymentLineResolvers[paymentLine.uuid] = null;
            resolver(isPaymentSuccessful);
        } else {
            paymentLine.handle_payment_response(isPaymentSuccessful);
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

                const result = await this._call_viva_wallet(
                    sessionId,
                    "viva_wallet_get_payment_status",
                    paymentLine
                );
                if ("success" in result && isPaymentStillValid()) {
                    clearInterval(intervalId);
                    if (this.isPaymentSuccessful(result)) {
                        this.handleSuccessResponse(paymentLine, result);
                        resolve(true);
                    } else {
                        this._show_error(_t("Message from Viva Wallet: %s", result.message));
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
            title = _t("Viva Wallet Error");
        }
        this.env.services.dialog.add(AlertDialog, {
            title: title,
            body: msg,
        });
    }
}
