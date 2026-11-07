import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    isForceDoneAllowed() {
        if (this.payment_method_id.payment_method_type === "glory_cash") {
            return false;
        }
        return super.isForceDoneAllowed();
    },
});
