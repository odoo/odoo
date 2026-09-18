import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { register_payment_method } from "@point_of_sale/app/services/pos_store";

export class PaymentPaymob extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        // Resolves the sendPaymentRequest promise once the callback arrives.
        this.webhookResolver = null;
    }

    async sendPaymentRequest(uuid) {
        await super.sendPaymentRequest(...arguments);
        const order = this.pos.getOrder();
        const line = order.getSelectedPaymentline();
        return line.amount < 0 ? this._paymobRefund(order, line) : this._paymobPay(order, line);
    }

    async _paymobPay(order, line) {
        const sessionId = this.pos.config.current_session_id.id;
        const paymentMethodId = line.payment_method_id.id;
        const infos = {
            amount_cents: Math.round(line.amount * 100),
            currency: this.pos.currency.name,
            // The timestamp keeps merchant_order_id unique per attempt; Paymob rejects re-registering an order id.
            merchant_order_id: `${sessionId}_${paymentMethodId}_${order.uuid}_${Date.now()}`,
        };

        line.setPaymentStatus("waitingCard");
        const response = await this.env.services.orm.silent.call(
            "pos.payment.method",
            "paymob_create_order",
            [[line.payment_method_id.id], infos]
        );

        if (!response || response.errorMessage || !response.id) {
            this._showError(
                response?.errorMessage ||
                    _t(
                        "Paymob could not register the order. Please check the payment method configuration."
                    )
            );
            line.setPaymentStatus("retry");
            return false;
        }

        return new Promise((resolve) => {
            this.webhookResolver = resolve;
        });
    }

    async _paymobRefund(order, line) {
        // Reversal targets the original sale's transaction, captured by updateRefundPaymentLine.
        const originalTransactionId = line.uiState.paymobRefundTransactionId;
        if (!originalTransactionId) {
            this._showError(
                _t(
                    "This payment cannot be refunded through Paymob: the original transaction is unknown."
                )
            );
            return false;
        }

        const infos = {
            transaction_id: originalTransactionId,
            amount_cents: Math.round(Math.abs(line.amount) * 100),
            currency: this.pos.currency.name,
        };

        line.setPaymentStatus("waitingCard");
        const response = await this.env.services.orm.silent.call(
            "pos.payment.method",
            "paymob_send_reversal",
            [[line.payment_method_id.id], infos]
        );

        if (
            !response ||
            response.errorMessage ||
            response.message !== "notification sent correctly"
        ) {
            this._showError(response?.errorMessage || _t("Paymob could not start the refund."));
            line.setPaymentStatus("retry");
            return false;
        }

        return new Promise((resolve) => {
            this.webhookResolver = resolve;
        });
    }

    async sendPaymentCancel(order, uuid) {
        await super.sendPaymentCancel(...arguments);
        // v1 has no void/cancel API: the cashier cancels on the terminal itself.
        this._showError(_t("Please cancel the payment directly on the Paymob terminal."));
        this.webhookResolver?.(false);
        this.webhookResolver = null;
        return true;
    }

    async handlePaymobWebhook() {
        const line = this.pos.getPendingPaymentLine("paymob");
        if (!line) {
            return;
        }
        const isRefund = line.amount < 0;
        // A refund callback carries the original sale's uuid (no link to the refund order).
        const criteria = isRefund
            ? { order_uuid: line.uiState.paymobRefundOrderUuid }
            : { order_uuid: line.pos_order_id.uuid };
        const result = await this.env.services.orm.silent.call(
            "pos.payment.method",
            "paymob_get_payment_status",
            [[line.payment_method_id.id], criteria]
        );
        if (!result) {
            return; // stale or unrelated callback
        }
        // A reversal re-sends the ORIGINAL transaction with is_voided/is_refunded flipped: same id,
        // same merchant_order_id, so only those two flags separate it from the sale callback.
        const isSuccessful =
            result.success &&
            (isRefund
                ? result.is_refunded || result.is_voided
                : !result.is_refunded && !result.is_voided);
        if (isSuccessful) {
            line.transaction_id = result.transaction_id;
            line.payment_ref_no = result.payment_ref_no;
            line.payment_method_authcode = result.payment_method_authcode;
            line.payment_method_payment_mode = result.payment_method_payment_mode;
            line.card_type = result.card_type;
            line.card_brand = result.card_brand;
            line.card_no = result.card_no;
            line.cardholder_name = result.cardholder_name;
            line.setPaymentStatus("done");
            this.webhookResolver?.(true);
        } else {
            this._showError(
                result.message ||
                    (isRefund
                        ? _t("The refund was declined by Paymob.")
                        : _t("The payment was declined by Paymob."))
            );
            line.setPaymentStatus("retry");
            this.webhookResolver?.(false);
        }
        this.webhookResolver = null;
    }

    _showError(msg, title) {
        this.env.services.dialog.add(AlertDialog, {
            title: title || _t("Paymob Error"),
            body: msg,
        });
    }
}

register_payment_method("paymob", PaymentPaymob);
