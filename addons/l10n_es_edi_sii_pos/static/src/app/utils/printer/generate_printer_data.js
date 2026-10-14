import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    generateReceiptData() {
        const data = super.generateReceiptData(...arguments);
        if (this.company.l10n_es_sii_required) {
            const order = this.order;
            const isRefund = Boolean(order.is_refund || order.refunded_order_id);
            data.extra_data.sii_ticket_name = this.getSiiTicketName();
            data.conditions.sii_invoiced =
                Boolean(order.to_invoice) || isRefund;
        }
        return data;
    },

    getSiiInvoiceName() {
        const order = this.order;
        return `${order.config.id}/${String(order.sequence_number).padStart(6, "0")}`;
    },
});
