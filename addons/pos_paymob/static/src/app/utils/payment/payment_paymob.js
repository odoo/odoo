import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ConnectionLostError } from "@web/core/network/rpc";
import { register_payment_method } from "@point_of_sale/app/services/pos_store";

// Fallback for a missed bus notification.
const POLLING_INTERVAL_MS = 5000;

export class PaymentPaymob extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.paymentLineResolvers = {};
        this.polledLineUuids = new Set();
    }

    async sendPaymentRequest() {
        await super.sendPaymentRequest(...arguments);
        const order = this.pos.getOrder();
        const line = order.getSelectedPaymentline();
        return line.amount < 0 ? this._paymobRefund(order, line) : this._paymobPay(order, line);
    }

    async _paymobPay(order, line) {
        const amountCents = Math.round(line.amount * 100);
        // A new order would leave the cancelled one payable too, so resend it.
        if (line.uiState.paymobOrderId && line.uiState.paymobAmountCents === amountCents) {
            return this._paymobResend(line);
        }
        const sessionId = this.pos.config.current_session_id.id;
        const paymentMethodId = line.payment_method_id.id;
        const infos = {
            amount_cents: amountCents,
            currency: this.pos.currency.name,
            // Paymob rejects a reused merchant_order_id.
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
        line.uiState.paymobOrderId = String(response.id);
        line.uiState.paymobMerchantOrderId = infos.merchant_order_id;
        line.uiState.paymobAmountCents = amountCents;
        return this.waitForPaymentConfirmation(line);
    }

    async _paymobResend(line) {
        line.setPaymentStatus("waitingCard");
        const response = await this.env.services.orm.silent.call(
            "pos.payment.method",
            "paymob_resend_order",
            [[line.payment_method_id.id], line.uiState.paymobMerchantOrderId]
        );
        if (
            !response ||
            response.errorMessage ||
            response.message !== "notification sent correctly"
        ) {
            this._showError(
                response?.errorMessage ||
                    _t("Paymob could not send the order to the terminal again.")
            );
            line.setPaymentStatus("retry");
            return false;
        }
        return this.waitForPaymentConfirmation(line);
    }

    async _paymobRefund(order, line) {
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

        return this.waitForPaymentConfirmation(line);
    }

    async sendPaymentCancel(order, uuid) {
        await super.sendPaymentCancel(...arguments);
        const line = order.payment_ids.find((paymentLine) => paymentLine.uuid === uuid);
        // Paymob can't withdraw an order already pushed to the terminal.
        this._showError(_t("Please cancel the payment directly on the Paymob terminal."));
        this._resolvePaymobLine(line, false);
        return true;
    }

    waitForPaymentConfirmation(line) {
        return new Promise((resolve) => {
            this.paymentLineResolvers[line.uuid] = resolve;
            this.pollPaymobPaymentStatus(line);
        });
    }

    async pollPaymobPaymentStatus(line) {
        if (this.polledLineUuids.has(line.uuid)) {
            return;
        }
        this.polledLineUuids.add(line.uuid);
        try {
            while (this.isPaymobLineOpen(line)) {
                await new Promise((resolve) => setTimeout(resolve, POLLING_INTERVAL_MS));
                await this.checkPaymobPaymentStatus(line);
            }
        } finally {
            this.polledLineUuids.delete(line.uuid);
        }
        if (!line.isDone()) {
            this._resolvePaymobLine(line, false);
        }
    }

    isPaymobLineOpen(line) {
        const isLineRemoved = !line.pos_order_id?.payment_ids.some(
            (paymentLine) => paymentLine.uuid === line.uuid
        );
        const status = line.getPaymentStatus();
        // The customer can still pay a cancelled sale on the terminal.
        const isCancelledSale = status === "retry" && line.uiState.paymobOrderId;
        return (
            !isLineRemoved && (["waitingCard", "waitingCancel"].includes(status) || isCancelledSale)
        );
    }

    _resolvePaymobLine(line, isSuccessful) {
        const resolve = this.paymentLineResolvers[line.uuid];
        delete this.paymentLineResolvers[line.uuid];
        resolve?.(isSuccessful);
    }

    async checkPaymobPaymentStatus(line) {
        const isRefund = line.amount < 0;
        const criteria = isRefund
            ? { transaction_id: String(line.uiState.paymobRefundTransactionId) }
            : {
                  paymob_order_id: line.uiState.paymobOrderId,
                  amount_cents: Math.round(line.amount * 100),
              };
        let result;
        try {
            result = await this.env.services.orm.silent.call(
                "pos.payment.method",
                "paymob_get_payment_status",
                [[line.payment_method_id.id], criteria]
            );
        } catch (error) {
            if (error instanceof ConnectionLostError) {
                return;
            }
            throw error;
        }
        if (
            !["waitingCard", "retry"].includes(line.getPaymentStatus()) ||
            !this.isPaymobLineOpen(line)
        ) {
            return;
        }
        if (!result) {
            return;
        }
        // A reversal re-sends the sale transaction: only is_refunded/is_voided tell them apart.
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
            this._resolvePaymobLine(line, true);
        } else if (line.getPaymentStatus() === "waitingCard") {
            // On a cancelled line, a decline is from an attempt already left.
            this._showError(
                result.message ||
                    (isRefund
                        ? _t("The refund was declined by Paymob.")
                        : _t("The payment was declined by Paymob."))
            );
            line.setPaymentStatus("retry");
            this._resolvePaymobLine(line, false);
        }
    }

    _showError(msg, title) {
        this.env.services.dialog.add(AlertDialog, {
            title: title || _t("Paymob Error"),
            body: msg,
        });
    }
}

register_payment_method("paymob", PaymentPaymob);
