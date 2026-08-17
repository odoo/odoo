import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { SelfOrder } from "@pos_self_order/app/services/self_order_service";

patch(SelfOrder.prototype, {
    async setup() {
        await super.setup(...arguments);
        const hasBancontactPaymentMethod = this.config.payment_method_ids.some(
            (pm) => pm.payment_provider === "bancontact_pay"
        );
        if (this.config.self_ordering_mode === "kiosk" && hasBancontactPaymentMethod) {
            this.data.connectWebSocket(
                "FINALIZE_BANCONTACT_PAY_KIOSK_PAYMENT",
                this._onFinalizeKioskPayment.bind(this)
            );
        }
    },

    _onFinalizeKioskPayment(args) {
        const payment = this.currentOrder?.payment_ids.find(
            (p) => p.bancontact_id === args.bancontact_id
        );
        if (!this.currentOrder || !payment || this.currentOrder.finalized || payment.isDone()) {
            return;
        }

        if (args.status === "success") {
            payment.setPaymentStatus("done");
            rpc(`/kiosk/payment/${this.config.id}/kiosk`, {
                order: this.currentOrder.serializeForORM(),
                access_token: this.access_token,
                payment_method_id: payment.payment_method_id.id,
            });
        } else {
            for (const p of this.currentOrder.payment_ids) {
                this.currentOrder.removePaymentline(p);
            }
            this.paymentError = true;
            this.notification.add(_t("Please try again or select another payment method"), {
                title: args.error || _t("Payment failed"),
                type: "danger",
            });
        }
    },
});
