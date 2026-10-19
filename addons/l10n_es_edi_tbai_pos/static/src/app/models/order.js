import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    waitForPushOrder() {
        return this.company.l10n_es_tbai_is_enabled ? true : super.waitForPushOrder(...arguments);
    },
});
