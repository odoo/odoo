import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    canEditPayment() {
        return ["FR", "MF", "MQ", "NC", "PF", "RE", "GF", "GP", "TF"].includes(
            this.company.country_id?.code
        )
            ? false
            : super.canEditPayment();
    },
});
