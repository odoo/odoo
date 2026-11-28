import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    get canEditPayment() {
        // The refund and the copy would be linked to the original's consolidated MyInvois document
        return this.company.country_id?.code === "MY" ? false : super.canEditPayment;
    },
});
