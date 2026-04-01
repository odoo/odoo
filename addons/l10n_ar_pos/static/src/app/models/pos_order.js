import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    isArgentineanCompany() {
        return this.company.country_id?.code == "AR";
    },
});
