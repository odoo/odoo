import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/generate_printer_data";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    generateData() {
        const data = super.generateData(...arguments);
        data.conditions.gcc_country = this.order.isGccCountry;
        data.conditions.l10n_gcc_dual_language_receipt = this.config.l10n_gcc_dual_language_receipt;
        data.conditions.l10n_gcc_is_settlement = this.order.isSettlement();
        return data;
    },
});
