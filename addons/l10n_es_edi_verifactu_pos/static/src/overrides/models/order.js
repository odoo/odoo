/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    //@override
    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(...arguments);
        if (this.pos.config.is_spanish && this.pos.config.l10n_es_edi_verifactu_required) {
            result.l10n_es_edi_verifactu_qr_code = this.l10n_es_edi_verifactu_qr_code;
        }
        return result;
    },
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        if (this.pos.config.is_spanish) {
            json.l10n_es_edi_verifactu_required = this.l10n_es_edi_verifactu_required;
        }
        return json;
    },
});
