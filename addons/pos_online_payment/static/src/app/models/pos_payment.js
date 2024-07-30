import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    //@override
    canBeAdjusted() {
        if (this.payment_method_id.payment_method_type === "online") {
            return false;
        } else {
            return super.canBeAdjusted();
        }
    },
});
