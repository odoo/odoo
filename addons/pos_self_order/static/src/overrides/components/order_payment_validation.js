import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";

patch(OrderPaymentValidation.prototype, {
    async finalizeValidation() {
        const result = await super.finalizeValidation(...arguments);
        if (this.order.source === "mobile") {
            await this.pos.updateSelfOrderCounts();
        }
        return result;
    },
});
