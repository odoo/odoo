import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    get displayName() {
        if (this.payment_method_id.use_sale_order_payment) {
            return this.name;
        }
        return super.displayName;
    },
});
