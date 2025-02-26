import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { sprintf } from "@web/core/utils/strings";
import { roundPrecision } from "@web/core/utils/numbers";
import { uuidv4 } from "@point_of_sale/utils";
import { register_payment_method } from "@point_of_sale/app/services/pos_store";

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
    sendPaymentRequest(uuid) {
        super.sendPaymentRequest(uuid);
        return this._vivaWalletPay(uuid);
    }
    sendPaymentCancel(order, uuid) {
        super.sendPaymentCancel(order, uuid);
        return this._vivaWalletCancel();
    }
    pendingVivaWalletLine() {
        return this.pos.getPendingPaymentLine("viva_wallet");
    }

    _callVivaWallet(data, action) {
        return this.env.services.orm.silent
            .call("pos.payment.method", action, [[this.payment_method_id.id], data])
            .catch(this._handleOdooConnectionFailure.bind(this));
    }

    _handleOdooConnectionFailure(data = {}) {
        // handle timeout
        var line = this.pendingVivaWalletLine();
        if (line) {
            line.setPaymentStatus("retry");
        }
        this._showError(
            _t(
                "Could not connect to the Odoo server, please check your internet connection and try again."
            )
        );

        return Promise.reject(data); // prevent subsequent onFullFilled's from being called
    }

    _vivaWalletHandleResponse(response) {
        var line = this.pendingVivaWalletLine();
        line.setPaymentStatus("waitingCard");
        if (response.error) {
            this._showError(response.error);
        }
        return this.waitForPaymentConfirmation();
    }

    _vivaWalletPay() {
        /**
         * Override
         */
        var order = this.pos.getOrder();
        const isRefundOrder = order._isRefundOrder();
        var line = order.getSelectedPaymentline();
        let customerTrns = " ";
        line.setPaymentStatus("waitingCard");

        if (line.amount < 0 && !isRefundOrder) {
            this._showError(_t("Cannot process transactions with negative amount."));
            return false;
        }

        if (order.partner) {
            customerTrns = order.partner.name + " - " + order.partner.email;
        }

        line.sessionId = order.uuid + " - " + uuidv4();
        var data = {
            sessionId: line.sessionId,
            terminalId: line.payment_method_id.viva_wallet_terminal_id,
            cashRegisterId: this.pos.getCashier().name,
            amount: roundPrecision(Math.abs(line.amount) * 100),
            currencyCode: this.pos.currency.iso_numeric.toString(),
            merchantReference: line.sessionId + "/" + this.pos.session.id,
            customerTrns: customerTrns,
            preauth: false,
            maxInstalments: 0,
            tipAmount: 0,
        };
        if (isRefundOrder) {
            data.parentSessionId = line.uiState.viva_wallet_session;
            return this._callVivaWallet(data, "viva_wallet_send_refund_request").then((data) =>
                this._vivaWalletHandleResponse(data)
            );
        }
        return this._callVivaWallet(data, "viva_wallet_send_payment_request").then((data) =>
            this._vivaWalletHandleResponse(data)
        );
    }

    async _vivaWalletCancel(order, uuid) {
        /**
         * Override
         */
        const line = this.pos.getOrder().getSelectedPaymentline();

        var data = {
            sessionId: line.sessionId,
            cashRegisterId: this.pos.getCashier().name,
        };
        return this._callVivaWallet(data, "viva_wallet_send_payment_cancel").then((data) => {
            if (data.error) {
                this._showError(data.error);
            }
            return true;
        });
    }

    /**
     * This method is called from pos_bus when the payment
     * confirmation from Viva Wallet is received via the webhook and confirmed in the retrieve_session_id.
     */
    async handleVivaWalletStatusResponse() {
        var line = this.pendingVivaWalletLine();
        const notification = await this.env.services.orm.silent.call(
            "pos.payment.method",
            "get_latest_viva_wallet_status",
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
            this._showError(sprintf(_t("Message from Viva Wallet: %s"), notification.error));
        }

        // when starting to wait for the payment response we create a promise
        // that will be resolved when the payment response is received.
        // In case this resolver is lost ( for example on a refresh ) we
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
            notification.sessionId == this.pendingVivaWalletLine().sessionId &&
            notification.success
        );
    }

    waitForPaymentConfirmation() {
        return new Promise((resolve) => {
            const paymentLine = this.pendingVivaWalletLine();
            const sessionId = paymentLine.sessionId;
            this.paymentLineResolvers[paymentLine.uuid] = resolve;
            const intervalId = setInterval(async () => {
                const isPaymentStillValid = () =>
                    this.paymentLineResolvers[paymentLine.uuid] &&
                    this.pendingVivaWalletLine()?.sessionId === sessionId &&
                    paymentLine.payment_status === "waitingCard";
                if (!isPaymentStillValid()) {
                    clearInterval(intervalId);
                    return;
                }

                const result = await this._callVivaWallet(
                    sessionId,
                    "viva_wallet_get_payment_status"
                );
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
        line.viva_wallet_session = notification.sessionId || "";
    }

    _showError(msg, title) {
        if (!title) {
            title = _t("Viva Wallet Error");
        }
        this.env.services.dialog.add(AlertDialog, {
            title: title,
            body: msg,
        });
    }
}

register_payment_method("viva_wallet", PaymentVivaWallet);
