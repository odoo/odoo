import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    exportForPrinting(baseUrl, headerData) {
        return {
            ...super.exportForPrinting(...arguments),
            is_gcc_country: ["SA", "AE", "BH", "OM", "QA", "KW"].includes(
                this.company.country_id?.code
            ),
        };
    },
});
