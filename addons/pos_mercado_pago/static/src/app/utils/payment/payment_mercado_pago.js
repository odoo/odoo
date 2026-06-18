import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";

// Delay before hinting the operator to refresh the terminal if the order has
// not been confirmed yet.
const REFRESH_HINT_DELAY = 30000;

export class PaymentMercadoPago extends PaymentInterface {
    async createOrder() {
        const order = this.pos.getOrder();
        const line = order.getSelectedPaymentline();
        // Build informations for creating a order on Mercado Pago.
        // Data in "external_reference" are send back with the webhook notification
        const infos = {
            type: "point",
            external_reference: `${this.pos.config.current_session_id.id}_${line.payment_method_id.id}_${order.uuid}`,
            transactions: {
                payments: [{ amount: this._formatAmount(line.amount) }],
            },
        };
        return await this.callPaymentMethod("mp_order_create", [
            [line.payment_method_id.id],
            infos,
        ]);
    }
    async getLastOrderStatus() {
        const line = this.pos.getOrder().getSelectedPaymentline();
        return await this.callPaymentMethod("mp_order_get", [
            [line.payment_method_id.id],
            this.mp_order.id,
        ]);
    }

    setup() {
        super.setup(...arguments);
        this.webhook_resolver = null;
        this.refresh_hint_timeout = null;
        this.mp_order = {};

        this.connectWebSocket("MERCADO_PAGO_LATEST_MESSAGE", (payload) => {
            if (payload.config_id === this.pos.config.id) {
                const pendingLine = this.pos.getPendingPaymentLine("mercado_pago");

                if (pendingLine && pendingLine.payment_method_id.id === payload.payment_method_id) {
                    pendingLine.payment_method_id.payment_terminal.handleMercadoPagoWebhook();
                }
            }
        });
    }

    async sendPaymentRequest(line) {
        await super.sendPaymentRequest(...arguments);
        if (line.amount < 0) {
            if (!this.pos.getOrder().isRefund) {
                this._showMsg(_t("Cannot process transactions with negative amount."), "error");
                return false;
            }
            return await this._refundOrder(line);
        }
        try {
            // During order creation, user can't cancel the order
            line.setPaymentStatus("waitingCapture");
            const mp_order = await this.createOrder();
            if (!("id" in mp_order)) {
                // 'errors': [{'code': '', 'message': '', 'details': [...]}]
                this._showMsg(
                    mp_order.errors
                        .map((e) =>
                            e.details?.length ? `${e.message}: ${e.details.join(", ")}` : e.message
                        )
                        .join("\n"),
                    "error"
                );
                return false;
            }
            // Order creation successful, save it
            this.mp_order = mp_order;
            line.transaction_id = mp_order.id;
            // After order creation, make canceling the order possible
            line.setPaymentStatus("waitingCard");
            // Warn the operator to refresh the terminal if nothing happens for
            // a while (e.g. the order did not reach the Point).
            this._startRefreshHint();
            // In test mode, simulate the terminal being tapped with a card.
            if (this.payment_method_id.mp_is_test_mode) {
                this.callPaymentMethod("mp_order_simulate", [
                    [line.payment_method_id.id],
                    mp_order.id,
                ]);
            }
            // Wait for order status change and return status result
            return await new Promise((resolve) => {
                this.webhook_resolver = resolve;
            });
        } catch (error) {
            this._showMsg(error, "System error");
            return false;
        }
    }

    async _refundOrder(line) {
        const original = this._findOriginalMpPayment(line);
        if (!original) {
            this._showMsg(
                _t("You can only refund an order that was paid for with Mercado Pago."),
                "error"
            );
            return false;
        }
        const refundAmount = Math.abs(line.amount);
        // Total refund uses an empty body; partial sends amount + payment id.
        const partialAmount =
            Math.abs(refundAmount - original.amount) < 0.01
                ? null
                : this._formatAmount(refundAmount);
        try {
            const result = await this.callPaymentMethod("mp_order_refund", [
                [line.payment_method_id.id],
                original.transactionId,
                partialAmount,
            ]);
            if (!("id" in result)) {
                this._showMsg(
                    result.message || result.errorMessage || _t("Refund failed"),
                    "error"
                );
                return false;
            }
            line.transaction_id = result.id;
            return true;
        } catch (error) {
            this._showMsg(error, "Refund error");
            return false;
        }
    }

    _findOriginalMpPayment(refundLine) {
        const orderToRefund = refundLine.pos_order_id.lines[0]?.refunded_orderline_id?.order_id;
        const matched = orderToRefund?.payment_ids.find(
            (l) => l.payment_method_id.payment_provider === "mercado_pago" && l.transaction_id
        );
        return matched ? { transactionId: matched.transaction_id, amount: matched.amount } : null;
    }

    async sendPaymentCancel(line) {
        await super.sendPaymentCancel(...arguments);
        if (!("id" in this.mp_order)) {
            return true;
        }
        this._showMsg(_t("Mercado Pago requires cancellations directly on the terminal."), "info");
        return true;
    }

    async handleMercadoPagoWebhook() {
        // No order id means either that the user reloaded the page or it is
        // an old webhook -> trash
        if (!("id" in this.mp_order)) {
            return;
        }
        let last_order_status = await this.getLastOrderStatus();
        // Mismatched id means it's an old webhook not related with the
        // current order -> trash
        if (this.mp_order.id !== last_order_status.id) {
            return;
        }

        // The terminal needs the customer to complete an action (e.g. CVV or
        // PIN). Tell the operator and keep waiting: do not resolve yet, the
        // final webhook (processed/rejected) will drive the outcome.
        if (last_order_status.status === "action_required") {
            this._clearRefreshHint();
            this._showMsg(_t("Complete the action on the Point device to continue."), "info");
            return;
        }

        const line = this.pos.getOrder().getSelectedPaymentline();
        const MAX_RETRY = 5;
        const RETRY_DELAY = 1000;

        const showMessageAndResolve = (messageKey, status, resolverValue) => {
            this._clearRefreshHint();
            if (!resolverValue) {
                this._showMsg(messageKey, status);
            }
            line.setPaymentStatus("done");
            this.webhook_resolver?.(resolverValue);
            return resolverValue;
        };

        const handleFinishedOrder = (order) => {
            if (order.status === "canceled") {
                return showMessageAndResolve(_t("Payment has been canceled"), "info", false);
            }
            if (order.status === "expired") {
                return showMessageAndResolve(_t("Payment expired"), "info", false);
            }
            // The payment is embedded in the order — no extra fetch needed.
            const payment = order.transactions?.payments?.[0];
            if (payment?.status === "processed") {
                return showMessageAndResolve(_t("Payment has been processed"), "info", true);
            }
            return showMessageAndResolve(_t("Payment has been rejected"), "info", false);
        };

        if (["processed", "canceled", "expired"].includes(last_order_status.status)) {
            return handleFinishedOrder(last_order_status);
        }
        if (["created", "at_terminal"].includes(last_order_status.status)) {
            // The order may still be transitioning (created -> at_terminal ->
            // processed) when the webhook fires; retry before giving up.
            return await new Promise((resolve) => {
                let retry_cnt = 0;
                const s = setInterval(async () => {
                    last_order_status = await this.getLastOrderStatus();
                    if (["processed", "canceled", "expired"].includes(last_order_status.status)) {
                        clearInterval(s);
                        resolve(handleFinishedOrder(last_order_status));
                    }
                    retry_cnt += 1;
                    if (retry_cnt >= MAX_RETRY) {
                        clearInterval(s);
                        resolve(
                            showMessageAndResolve(
                                _t("Payment status could not be confirmed"),
                                "error",
                                false
                            )
                        );
                    }
                }, RETRY_DELAY);
            });
        }
        return showMessageAndResolve(_t("Unknown payment status"), "error", false);
    }

    // private methods
    _startRefreshHint() {
        this._clearRefreshHint();
        this.refresh_hint_timeout = setTimeout(() => {
            this._showMsg(
                _t(
                    "If the payment does not appear on the Point, press the 'Refresh' button on the device."
                ),
                "info"
            );
        }, REFRESH_HINT_DELAY);
    }

    _clearRefreshHint() {
        if (this.refresh_hint_timeout) {
            clearTimeout(this.refresh_hint_timeout);
            this.refresh_hint_timeout = null;
        }
    }

    _formatAmount(amount) {
        // Mercado Pago expects amounts as strings with up to 2 decimal places;
        // honor the currency's decimal_places to avoid sending fractional units
        // for currencies that do not have them (e.g. CLP).
        const decimals = Math.min(this.pos.currency.decimal_places ?? 2, 2);
        return amount.toFixed(decimals);
    }

    _showMsg(msg, title) {
        this.env.services.dialog.add(AlertDialog, {
            title: "Mercado Pago " + title,
            body: msg,
        });
    }
}

registry.category("pos_payment_providers").add("mercado_pago", PaymentMercadoPago);
