/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    //@override
    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(...arguments);
        result.l10n_es_pos_tbai_qrsrc = this.l10n_es_pos_tbai_qrsrc;
        return result;
    },
    wait_for_push_order() {
        return this.company.l10n_es_tbai_is_enabled
            ? true
            : super.wait_for_push_order(...arguments);
    },
});
