import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/generate_printer_data";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    generateData() {
        const data = super.generateData(...arguments);

        if (this.is_l10n_es_simplified_invoice) {
            data.extra_data.invoice_name = this.invoice_name; // Previously set in payment validation
        }

        return data;
    },
});
