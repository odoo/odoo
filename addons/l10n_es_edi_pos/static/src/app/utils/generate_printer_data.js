import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";
import { patch } from "@web/core/utils/patch";

/**
 * Mirror of `pos.order.receipt.order_receipt_generate_data` in l10n_es_edi_pos.
 */
patch(GeneratePrinterData.prototype, {
    generateReceiptData() {
        const data = super.generateReceiptData(...arguments);
        if (!this.order.l10nEsPosFiscalMode) {
            return data;
        }

        data.conditions.l10n_es_pos_edi = true;

        const simplifiedPartnerId = this.config._l10n_es_pos_simplified_partner_id;
        if (simplifiedPartnerId && this.order.partner_id?.id === simplifiedPartnerId) {
            data.partner = false;
        }

        const invoiceName = this.order.l10nEsPosInvoiceName;
        data.conditions.l10n_es_pos_invoice_name = Boolean(invoiceName);
        data.conditions.l10n_es_pos_simplified_invoice = this.order.l10nEsPosIsSimplifiedInvoice;
        data.conditions.l10n_es_pos_simplified_credit_note = 
            this.order.l10nEsPosIsSimplifiedCreditNote;
        data.extra_data.l10n_es_pos_invoice_name = invoiceName;
        return data;
    },
});
