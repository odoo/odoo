import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    generateReceiptData() {
        const data = super.generateReceiptData(...arguments);
        if (this.order.isBHCompany()) {
            data.conditions.code_bh = true;
            data.conditions.l10n_bh_partner_has_vat = Boolean(
                this.order.partner_id?.commercial_partner_id?.vat
            );
        }
        return data;
    },
});
