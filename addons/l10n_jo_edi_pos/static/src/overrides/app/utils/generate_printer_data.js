import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";
import { patch } from "@web/core/utils/patch";
import { qrCodeSrc } from "@point_of_sale/utils";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    generateData() {
        const data = super.generateData(...arguments);
        if (this.order.company.country_id?.code === "JO") {
            data.extra_data.l10n_jo_edi_pos_qr = qrCodeSrc(this.order.l10n_jo_edi_pos_qr);
        }
        return data;
    },
});
