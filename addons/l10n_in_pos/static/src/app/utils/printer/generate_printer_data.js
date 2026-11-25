import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    generateReceiptData() {
        const data = super.generateReceiptData(...arguments);

        if (this.order.isInCompany) {
            data.conditions.code_in = this.order.isInCompany;
            data.extra_data.l10n_in_hsn_summary = this.order._prepareL10nInHsnSummary();
            data.extra_data.l10n_in_invoice_number =
                (this.order.is_singly_invoiced && this.order.invoiceName) ||
                this.order.l10n_in_b2c_invoice_number;
        }

        return data;
    },
});
