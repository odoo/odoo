import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/generate_printer_data";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    generateData() {
        const data = super.generateData(...arguments);

        if (this.order.l10n_es_edi_verifactu_qr_code) {
            const baseUrl = this.order.config._base_url;
            data.image.l10n_es_edi_verifactu_qr_code = this.generateQrCode(
                `${baseUrl}/${this.order.l10n_es_edi_verifactu_qr_code}`
            );
        }

        return data;
    },
});
