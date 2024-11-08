import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    //@override
    exportForPrinting(baseUrl, headerData) {
        const result = super.exportForPrinting(...arguments);
        result.l10n_es_pos_tbai_qrsrc = this.l10n_es_pos_tbai_qrsrc;
        return result;
    },
    waitForPushOrder() {
        return this.company.l10n_es_tbai_is_enabled ? true : super.waitForPushOrder(...arguments);
    },
});
