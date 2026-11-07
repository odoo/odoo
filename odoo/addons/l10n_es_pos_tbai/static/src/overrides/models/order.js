/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    //@override
    export_for_printing() {
        return {
            ...super.export_for_printing(...arguments),
            l10n_es_pos_tbai_qrsrc: this.l10n_es_pos_tbai_qrsrc,
        };
    },
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        if (this.pos.config.is_spanish) {
            json["l10n_es_tbai_refund_reason"] = this.l10n_es_tbai_refund_reason
        }
        return json;
    },
});
