/** @odoo-module */

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
    send_payment_request(cid) {
        super.send_payment_request(cid);
        return this._viva_wallet_pay(cid);
    }
    send_payment_cancel(order, cid) {
        super.send_payment_cancel(order, cid);
        return this._viva_wallet_cancel();
    }
    pending_viva_wallet_line() {
        return this.pos.getPendingPaymentLine("viva_wallet");
    }

    _call_viva_wallet(data, action) {
        return this.env.services.orm.silent
            .call("pos.payment.method", action, [[this.payment_method.id], data])
            .catch(this._handle_odoo_connection_failure.bind(this));
    }

    _handle_odoo_connection_failure(data = {}) {
        // handle timeout
        var line = this.pending_viva_wallet_line();
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

    _viva_wallet_handle_response(response) {
        var line = this.pending_viva_wallet_line();
        line.set_payment_status("waitingCard");
        if (response.error) {
            this._show_error(response.error);
        }
        return this.waitForPaymentConfirmation();
    }

    _viva_wallet_pay() {
        /**
         * Override
         */
        super.send_payment_request(...arguments);
        var order = this.pos.get_order();
        var line = order.selected_paymentline;
        let customerTrns = " ";
        line.set_payment_status("waitingCard");

        if (line.amount < 0) {
            this._show_error(_t("Cannot process transactions with negative amount."));
            return false;
        }

        if (order.partner) {
            customerTrns = order.partner.name + " - " + order.partner.email;
        }

        line.sessionId = order.uid + " - " + uuidv4();
        var data = {
            sessionId: line.sessionId,
            terminalId: line.payment_method.viva_wallet_terminal_id,
            cashRegisterId: this.pos.get_cashier().name,
            amount: roundPrecision(line.amount * 100),
            currencyCode: "978", // Viva wallet only uses EUR 978 need add a new field numeric_code in res.currency
            merchantReference: line.sessionId + "/" + this.pos.session.id,
            customerTrns: customerTrns,
            preauth: false,
            maxInstalments: 0,
            tipAmount: 0,
        };
        return this._call_viva_wallet(data, "viva_wallet_send_payment_request").then((data) => {
            return this._viva_wallet_handle_response(data);
        });
    }

    async _viva_wallet_cancel(order, cid) {
        /**
         * Override
         */
        super.send_payment_cancel(...arguments);
        const line = this.pos.get_order().selected_paymentline;

        var data = {
            sessionId: line.sessionId,
            cashRegisterId: this.pos.get_cashier().name,
        };
        return this._call_viva_wallet(data, "viva_wallet_send_payment_cancel").then((data) => {
            if (data.error) {
                this._show_error(data.error);
            }
            return true;
        });
    }

    /**
     * This method is called from pos_bus when the payment
     * confirmation from Viva Wallet is received via the webhook and confirmed in the retrieve_session_id.
     */
    async handleVivaWalletStatusResponse() {
        var line = this.pending_viva_wallet_line();
        const notification = await this.env.services.orm.silent.call(
            "pos.payment.method",
            "get_latest_viva_wallet_status",
            [[this.payment_method.id]]
        );

        if (!notification) {
            this._handle_odoo_connection_failure();
            return;
        }

        const isPaymentSuccessful = this.isPaymentSuccessful(notification);
        if (isPaymentSuccessful) {
            this.handleSuccessResponse(line, notification);
        } else {
            this._show_error(sprintf(_t("Message from Viva Wallet: %s"), notification.error));
        }

        // when starting to wait for the payment response we create a promise
        // that will be resolved when the payment response is received.
        // In case this resolver is lost ( for example on a refresh ) we
        // we use the handle_payment_response method on the payment line
        const resolver = this.paymentLineResolvers?.[line.cid];
        if (resolver) {
            this.paymentLineResolvers[line.cid] = null;
            resolver(isPaymentSuccessful);
        } else {
            line.handle_payment_response(isPaymentSuccessful);
        }
    }

    isPaymentSuccessful(notification) {
        return (
            notification &&
            notification.sessionId == this.pending_viva_wallet_line().sessionId &&
            notification.success
        );
    }

    waitForPaymentConfirmation() {
        return new Promise((resolve) => {
            const paymentLine = this.pending_viva_wallet_line();
            this.paymentLineResolvers[paymentLine.cid] = resolve;
            const intervalId = setInterval(async () => {
                if (!this.paymentLineResolvers[paymentLine.cid]) {
                    clearInterval(intervalId);
                    return;
                }

                const result = await this._call_viva_wallet(
                    paymentLine.sessionId,
                    "viva_wallet_get_payment_status"
                );
                if ("success" in result && this.paymentLineResolvers[paymentLine.cid]) {
                    clearInterval(intervalId);
                    if (this.isPaymentSuccessful(result)) {
                        this.handleSuccessResponse(paymentLine, result);
                        resolve(true);
                    } else {
                        resolve(false);
                    }
                    this.paymentLineResolvers[paymentLine.cid] = null;
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
            title = _t("Viva Wallet Error");
        }
        this.env.services.dialog.add(AlertDialog, {
            title: title,
            body: msg,
        });
    }
}
