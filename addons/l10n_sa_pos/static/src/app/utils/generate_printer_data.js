import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/generate_printer_data";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    generateData() {
        const data = super.generateData(...arguments);
        if (this.order.isSACompany()) {
            data.conditions.code_sa = true;
            data.image.sa_qr_code = this.order.generateQrcode();
        }
        return data;
    },
});
