import { patch } from "@web/core/utils/patch";
import { SelfOrder } from "@pos_self_order/app/services/self_order_service";

patch(SelfOrder.prototype, {
    filterPaymentMethods(pms) {
        const otherPaymentMethods = super.filterPaymentMethods(...arguments);
        const vivaPaymentMethods = pms.filter((rec) => rec.use_payment_terminal === "viva_com");
        return [...new Set([...otherPaymentMethods, ...vivaPaymentMethods])];
    },
});
