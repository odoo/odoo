import { patch } from "@web/core/utils/patch";
import { SelfOrder } from "@pos_self_order/app/services/self_order_service";
import { QFPay, QFPayError } from "@pos_qfpay/app/qfpay";

patch(SelfOrder.prototype, {
    async setup() {
        await super.setup(...arguments);

        const QFPayPaymentMethod = this.models["pos.payment.method"].find(
            (p) => p.use_payment_terminal === "qfpay"
        );

        if (QFPayPaymentMethod) {
            this.qfpay = new QFPay(this.env, QFPayPaymentMethod, this.handleQFPayError.bind(this));
        }
    },

    filterPaymentMethods(pms) {
        const pm = super.filterPaymentMethods(...arguments);
        const qfpay_pm = pms.filter((rec) => rec.use_payment_terminal === "qfpay");
        return [...new Set([...pm, ...qfpay_pm])];
    },

    handleQFPayError(error, type) {
        this.paymentError = true;
        this.handleErrorNotification(error, type);
    },

    handleErrorNotification(error, type = "danger") {
        let errorMessage = "";
        if (error instanceof QFPayError) {
            errorMessage = `QFPay POS: ${error.message}`;
            this.notification.add(errorMessage, {
                type: type,
            });
        } else {
            super.handleErrorNotification(...arguments);
        }
    },
});
