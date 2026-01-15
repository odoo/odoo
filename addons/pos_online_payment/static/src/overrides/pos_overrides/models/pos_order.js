import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    canBeValidated() {
        const hasOnlinePayment = this.payment_ids?.some(
            (p) => p?.payment_method_id?.is_online_payment
        );
        if (hasOnlinePayment && typeof this.id !== "number") {
            return false;
        }
        return super.canBeValidated();
    },
});
