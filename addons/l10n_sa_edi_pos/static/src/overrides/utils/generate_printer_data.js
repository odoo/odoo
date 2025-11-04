import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/generate_printer_data";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    generateData() {
        const data = super.generateData(...arguments);
        data.conditions.code_sa = this.order.isSACompany();
        data.conditions.l10n_sa_not_legal = this.order.notLegal;
        return data;
    },
});
