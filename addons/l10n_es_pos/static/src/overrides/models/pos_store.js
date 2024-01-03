/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    getReceiptHeaderData(order) {
        const result = super.getReceiptHeaderData(...arguments);
        result.is_spanish = this.config.is_spanish;
        result.simplified_partner_id = this.config.simplified_partner_id.id;
        if (order) {
            result.is_l10n_es_simplified_invoice = order.is_l10n_es_simplified_invoice;
            result.partner = order.get_partner();
            result.invoice_name = order.invoice_name;
        }
        return result;
    },
});
