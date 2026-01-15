import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    waitForPushOrder() {
        return this.company.l10n_es_edi_verifactu_required
            ? true
            : super.waitForPushOrder(...arguments);
    },
});
