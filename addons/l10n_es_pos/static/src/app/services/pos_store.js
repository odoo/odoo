import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
<<<<<<< 1c4a9c4884e140652d791d81f68bdf48d56d5086:addons/l10n_es_pos/static/src/app/services/pos_store.js
||||||| 95ed5c75582631c7cc417b000569ff6451cc5006:addons/l10n_es_pos/static/src/overrides/models/pos_store.js
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
=======
    getReceiptHeaderData(order) {
        const result = super.getReceiptHeaderData(...arguments);
        result.is_spanish = this.config.is_spanish;
        result.simplified_partner_id = this.config.simplified_partner_id?.id;
        if (order) {
            result.is_l10n_es_simplified_invoice = order.is_l10n_es_simplified_invoice;
            result.partner = order.get_partner();
            result.invoice_name = order.invoice_name;
        }
        return result;
    },
>>>>>>> 63975034c43bef7550f86ca6fc1c9af17825134c:addons/l10n_es_pos/static/src/overrides/models/pos_store.js
    _getCreateOrderContext(orders, options) {
        let context = super._getCreateOrderContext(...arguments);
        if (this.config.is_spanish) {
            const noOrderRequiresInvoicePrinting = orders.every(
                (order) => !order.to_invoice && order.data.is_l10n_es_simplified_invoice
            );
            if (noOrderRequiresInvoicePrinting) {
                context = { ...context, generate_pdf: false };
            }
        }
        return context;
    },
});
