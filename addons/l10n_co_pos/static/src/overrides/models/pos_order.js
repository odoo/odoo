import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    is_colombian_country() {
        return this.company.country_id?.code === "CO";
    },
    exportForPrinting(baseUrl, headerData) {
        const result = super.exportForPrinting(...arguments);
        result.l10n_co_dian = this.name;
        return result;
    },
    waitForPushOrder() {
        var result = super.waitForPushOrder(...arguments);
        result = Boolean(result || this.is_colombian_country());
        return result;
    },
});
