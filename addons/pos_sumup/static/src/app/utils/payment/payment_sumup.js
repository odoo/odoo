import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";

export const POLLING_INTERVAL_MS = 5000;
export const POLLING_START_DELAY_MS = 60000;

export class PaymentSumup extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.pending = new Map();
        this.connectWebSocket("SUMUP_LATEST_RESPONSE", (data) => {
            const paymentLine = this.pos.models["pos.payment"].find(
                (line) => line.transaction_id === data.client_transaction_id
            );

            if (
                paymentLine &&
                !paymentLine.isDone() &&
                paymentLine.getPaymentStatus() !== "retry"
            ) {
                paymentLine.payment_method_id.payment_interface.handleSumupStatusResponse(
                    paymentLine,
                    data
                );
            }
        });
    }

    async sendPaymentRequest(line) {
        await super.sendPaymentRequest(...arguments);

        const isRefund = line.amount < 0;
        const method = isRefund ? "sumup_refund" : "sumup_pay";
        const params = [[this.payment_method_id.id], line.amount];
        if (isRefund) {
            params.push(line.transaction_id);
        }

        const response = await this.callPaymentMethod(method, params);
        if (response?.error) {
            this._notifySumupError(response.error.message);
            return false;
        }
        if (isRefund) {
            return true;
        }

        line.transaction_id = response.data?.client_transaction_id;
        const { promise, resolve } = Promise.withResolvers();
        const pending = {
            checkoutId: response.data?.checkout_id,
            resolve,
        };
        pending.timeout = setTimeout(() => {
            pending.interval = setInterval(
                () => this._pollCheckoutStatus(line),
                POLLING_INTERVAL_MS
            );
        }, POLLING_START_DELAY_MS);
        this.pending.set(line.uuid, pending);
        return promise;
    }

    async sendPaymentCancel(line) {
        await super.sendPaymentCancel(...arguments);
        this._stopPolling(line);
        const cancelSumup = await this.callPaymentMethod("sumup_cancel", [
            [this.payment_method_id.id],
        ]);
        if (cancelSumup) {
            line.setPaymentStatus("retry");
            return true;
        }
    }

    _stopPolling(line) {
        const pending = this.pending.get(line.uuid);
        clearTimeout(pending?.timeout);
        clearInterval(pending?.interval);
        this.pending.delete(line.uuid);
    }

    /**
     * Polling fallback for a payment only: asks SumUp directly for the reader
     * checkout's live status, in case the webhook notification is lost entirely.
     */
    async _pollCheckoutStatus(line) {
        const pending = this.pending.get(line.uuid);
        if (!pending) {
            return;
        }
        const response = await this.callPaymentMethod("sumup_get_checkout_status", [
            [this.payment_method_id.id],
            pending.checkoutId,
        ]);
        if (!response) {
            return;
        }
        this.handleSumupStatusResponse(line, response.data);
    }

    handleSumupStatusResponse(line, data) {
        if (data.status === "failed") {
            this._notifySumupError(data?.failure_reason || _t("Payment failed."));
        }
        const resolve = this.pending.get(line.uuid)?.resolve;
        this._stopPolling(line);
        if (resolve) {
            resolve(data.status === "successful");
        } else {
            line.handlePaymentResponse(data.status === "successful");
        }
    }

    _notifySumupError(body) {
        this.env.services.dialog.add(AlertDialog, {
            title: _t("SumUp Error"),
            body,
        });
    }
}

registry.category("pos_payment_providers").add("sumup", PaymentSumup);
