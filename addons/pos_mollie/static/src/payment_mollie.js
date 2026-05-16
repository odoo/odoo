import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { register_payment_method } from "@point_of_sale/app/services/pos_store";

export class PaymentMollie extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.paymentLineResolvers = {};
    }

    async sendPaymentRequest(uuid) {
        const paymentLine = this.pos.getOrder().getPaymentlineByUuid(uuid);
        if (paymentLine.amount < 0) {
            const originalPaymentId = this._findOriginalPaymentId(paymentLine);
            if (!originalPaymentId) {
                this._showMollieError(
                    _t("You can only refund an order that was paid for with Mollie.")
                );
                return false;
            }

            return this._createMollieRefund(paymentLine, originalPaymentId);
        }

        return this._createMolliePayment(paymentLine);
    }

    async sendPaymentCancel(order, uuid) {
        const paymentLine = this.pos.getOrder().getPaymentlineByUuid(uuid);
        try {
            await this.pos.data.call("pos.payment.method", "mollie_cancel_payment", [
                this.payment_method_id.id,
                paymentLine.transaction_id,
            ]);
            return true;
        } catch (error) {
            this._showMollieError(error);
            return false;
        }
    }

    async _createMolliePayment(paymentLine) {
        try {
            const data = await this.pos.data.call("pos.payment.method", "mollie_create_payment", [
                this.payment_method_id.id,
                paymentLine.amount,
                paymentLine.uuid,
                this.pos.session.id,
            ]);
            if (!["open", "pending"].includes(data.status)) {
                this._showMollieError(_t("Failed to initiate payment: %s", data.status));
                return false;
            }

            // In test mode, the terminal is simulated using a popup
            if (data._links.changePaymentState) {
                browser.open(data._links.changePaymentState.href, "_blank");
            }

            paymentLine.transaction_id = data.id;
            await this.pos.data.synchronizeLocalDataInIndexedDB();

            const { promise, resolve } = Promise.withResolvers();
            this.paymentLineResolvers[paymentLine.uuid] = resolve;

            return promise;
        } catch (error) {
            this._showMollieError(error);
            return false;
        }
    }

    async _createMollieRefund(refundPaymentLine, originalPaymentId) {
        try {
            const data = await this.pos.data.call("pos.payment.method", "mollie_create_refund", [
                this.payment_method_id.id,
                originalPaymentId,
                Math.abs(refundPaymentLine.amount),
                refundPaymentLine.uuid,
                this.pos.session.id,
            ]);

            if (!["queued", "pending"].includes(data.status)) {
                this._showMollieError(_t("Failed to initiate refund: %s", data.status));
                return false;
            }

            refundPaymentLine.transaction_id = data.id;
            return true;
        } catch (error) {
            this._showMollieError(error);
            return false;
        }
    }

    _findOriginalPaymentId(refundPaymentLine) {
        const currentOrder = refundPaymentLine.pos_order_id;
        const orderToRefund = currentOrder.lines[0]?.refunded_orderline_id?.order_id;
        if (!orderToRefund) {
            return null;
        }

        const amountDue = Math.abs(currentOrder.remainingDue);
        const matchedPaymentLine = orderToRefund.payment_ids.find(
            (line) =>
                line.payment_method_id.use_payment_terminal === "mollie" && line.amount <= amountDue
        );

        return matchedPaymentLine?.transaction_id ?? null;
    }

    handleMollieStatusResponse(paymentLine, notification) {
        const isSuccessful = notification.status === "paid";

        if (isSuccessful) {
            paymentLine.card_no = notification.card_no;
            paymentLine.card_type = notification.card_type;
            paymentLine.card_brand = notification.card_brand;
        }

        if (notification.status === "failed") {
            this._showMollieError(
                notification.status_reason?.message ??
                    _t("The payment failed for an unknown reason.")
            );
        }
        if (notification.status === "expired") {
            this._showMollieError(_t("The payment has timed out."));
        }

        const resolver = this.paymentLineResolvers?.[paymentLine.uuid];
        if (resolver) {
            this.paymentLineResolvers[paymentLine.uuid] = null;
            resolver(isSuccessful);
        } else {
            paymentLine.handlePaymentResponse(isSuccessful);
        }
    }

    _extractErrorMessage(error) {
        if (typeof error === "string") {
            return error;
        }
        if (error.name === "RPC_ERROR") {
            return error.data.message;
        }
        return error.message;
    }

    _showMollieError(error) {
        this.env.services.dialog.add(AlertDialog, {
            title: _t("Mollie Error"),
            body: this._extractErrorMessage(error),
        });
    }
}

register_payment_method("mollie", PaymentMollie);
