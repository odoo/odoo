import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";

patch(GeneratePrinterData.prototype, {
    generateReceiptData() {
        const data = super.generateReceiptData(...arguments);

        if (this.order.isInCompany) {
            data.conditions.code_in = this.order.isInCompany;
            data.extra_data.l10n_in_hsn_summary = this.order._prepareL10nInHsnSummary();
            // B2C orders show their B2C invoice number, B2B orders the number of their invoice.
            data.extra_data.l10n_in_invoice_number =
                (this.order.isToInvoice() && this.order.account_move?.name) ||
                this.order.l10n_in_b2c_invoice_number;
        }

        return data;
    },
});
