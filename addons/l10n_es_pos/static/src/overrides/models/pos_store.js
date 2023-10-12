/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    getReceiptHeaderData() {
        return {
            ...super.getReceiptHeaderData(...arguments),
            is_spanish: this.config.is_spanish,
            simplified_partner_id: this.config.simplified_partner_id[0],
            is_l10n_es_simplified_invoice: this.get_order().is_l10n_es_simplified_invoice,
            partner: this.get_order().get_partner(),
            invoice_name: this.get_order().invoice_name,
        };
    },
});
