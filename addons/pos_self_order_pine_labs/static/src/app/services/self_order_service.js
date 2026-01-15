import { patch } from "@web/core/utils/patch";
import { SelfOrder } from "@pos_self_order/app/services/self_order_service";
import { PineLabs, PineLabsError } from "@pos_self_order_pine_labs/app/pine_labs";
import { _t } from "@web/core/l10n/translation";

patch(SelfOrder.prototype, {
    async setup() {
        await super.setup(...arguments);

        const pineLabsPaymentMethod = this.models["pos.payment.method"].find(
            (p) => p.use_payment_terminal === "pine_labs"
        );

        if (pineLabsPaymentMethod) {
            this.pineLabs = new PineLabs(
                pineLabsPaymentMethod,
                this.access_token,
                this.config,
                this.handlePineLabsError.bind(this)
            );
        }
    },

    filterPaymentMethods(pms) {
        const filteredPaymentMethods = super.filterPaymentMethods(...arguments);
        const pineLabsPaymentMethods = pms.filter(
            (rec) => rec.use_payment_terminal === "pine_labs"
        );
        return [...new Set([...filteredPaymentMethods, ...pineLabsPaymentMethods])];
    },

    handlePineLabsError(error, type) {
        this.paymentError = true;
        this.handleErrorNotification(error, type);
    },

    handleErrorNotification(error, type = "danger") {
        if (error instanceof PineLabsError) {
            this.notification.add(
                _t(`Pine Labs Error: %(errorMessage)s`, { errorMessage: error.message || "" }),
                {
                    type: type,
                }
            );
        } else {
            super.handleErrorNotification(...arguments);
        }
    },
});
