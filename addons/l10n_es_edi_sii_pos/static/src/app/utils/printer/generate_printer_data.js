import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    generateReceiptData() {
        const data = super.generateReceiptData(...arguments);
        if (this.company.l10n_es_sii_required && !this.order.account_move) {
            data.extra_data.sii_ticket_name = this.getSiiInvoiceName();
            data.conditions.has_account_move = Boolean(this.order.account_move) || Boolean(this.order.to_invoice);
        }
        return data;
    },

    getSiiInvoiceName() {
        const order = this.order;
        return `${order.config.id}/${String(order.sequence_number).padStart(6, "0")}`;
    }
});
