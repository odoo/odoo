/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { qrCodeSrc } from "@point_of_sale/utils";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    get isSACompany() {
        return this.company.country?.code == "SA";
    },
    getReceiptHeaderData(order) {
        const result = super.getReceiptHeaderData(...arguments);
        if (order && this.isSACompany && !result.is_settlement) {
            // is_settlement is assigned in super l10n_sa_pos
            result.not_legal = !order.l10n_sa_invoice_qr_code_str;
            result.qr_code = result.not_legal ? "" : qrCodeSrc(order.l10n_sa_invoice_qr_code_str);
        }
        return result;
    },
    async push_single_order(order) {
        const result = await super.push_single_order(...arguments);
        if (order && this.isSACompany && result?.length) {
            order.l10n_sa_invoice_qr_code_str = result[0].l10n_sa_invoice_qr_code_str;
            order.account_move = result[0].account_move;
        }
        return result;
    },

    _getCreateOrderContext() {
        const context = super._getCreateOrderContext(...arguments);
        // The invoice is submitted to ZATCA after the PDF would be generated, which would then
        // lack the QR code: defer the PDF until the invoice is downloaded.
        if (this.isSACompany) {
            context.generate_pdf = false;
        }
        return context;
    },
});
