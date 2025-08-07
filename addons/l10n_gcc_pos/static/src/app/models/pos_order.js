import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    get isGccCountry() {
        return ["SA", "AE", "BH", "OM", "QA", "KW"].includes(this.company.country_id?.code);
    },
    get showTitle() {
        return this.state !== "draft";
    },
});
