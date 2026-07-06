import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    generateReceiptData() {
        const data = super.generateReceiptData(...arguments);
        data.conditions.code_sa = this.order.isInvoiceMandatoryForSA();
        data.conditions.l10n_sa_not_legal =
            this.order.notLegal || !this.order.config._l10n_sa_is_on_phase_2;
        return data;
    },
});
