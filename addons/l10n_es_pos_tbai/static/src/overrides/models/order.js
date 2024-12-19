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
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        if (this.pos.config.is_spanish) {
            json["l10n_es_tbai_refund_reason"] = this.l10n_es_tbai_refund_reason;
        }
        return json;
    },
    serialize() {
        const result = super.serialize(...arguments);
        result.l10n_es_tbai_refund_reason = this.l10n_es_tbai_refund_reason;
        return result;
    },
});
