/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    //@override
    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(...arguments);
        if (this.company.l10n_es_edi_verifactu_required) {
            result.l10n_es_edi_verifactu_qr_code = this.l10n_es_edi_verifactu_qr_code;
        }
        return result;
    },
});
