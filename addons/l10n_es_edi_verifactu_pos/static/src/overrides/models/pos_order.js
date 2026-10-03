/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { roundCurrency } from "@point_of_sale/app/models/utils/currency";

patch(PosOrder.prototype, {
    //@override
    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(...arguments);
        if (this.company.l10n_es_edi_verifactu_required) {
            result.l10n_es_edi_verifactu_qr_code = this.l10n_es_edi_verifactu_qr_code;
            result.invoice_name = `${this.config.id}/${String(this.sequence_number).padStart(6, "0")}`;
            result.is_simplified = !this.to_invoice && this.isSimplifiedInvoice();
        }
        return result;
    },
    isSimplifiedInvoice() {
        // if l10n_es_pos is not installed, we take the default limit of 400
        return (
            roundCurrency(this.get_total_with_tax(), this.currency) <
                (this.company.l10n_es_simplified_invoice_limit || 400)
        );
    },
});
