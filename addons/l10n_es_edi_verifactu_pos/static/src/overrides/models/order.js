/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    wait_for_push_order() {
        return this.pos.config.l10n_es_edi_verifactu_required ? true : super.wait_for_push_order(...arguments);
    },
    //@override
    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(...arguments);
        if (this.pos.config.l10n_es_edi_verifactu_required) {
            result.l10n_es_edi_verifactu_qr_code = this.l10n_es_edi_verifactu_qr_code;
        }
        return result;
    },
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.l10n_es_edi_verifactu_required = this.l10n_es_edi_verifactu_required;
        if (this.l10n_es_edi_verifactu_required) {
            json.l10n_es_edi_verifactu_refund_reason = this.l10n_es_edi_verifactu_refund_reason;
        }
        return json;
    },
});
