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
<<<<<<< 18.0:addons/l10n_es_edi_tbai_pos/static/src/overrides/models/order.js
    wait_for_push_order() {
        return this.company.l10n_es_tbai_is_enabled
            ? true
            : super.wait_for_push_order(...arguments);
||||||| 30173a29155102959f655a6cf0debb3e7b39e9ff:addons/l10n_es_pos_tbai/static/src/overrides/models/order.js
=======
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
>>>>>>> b715eea345f59f82d17017483fa08bc88a403ada:addons/l10n_es_pos_tbai/static/src/overrides/models/order.js
    },
});
