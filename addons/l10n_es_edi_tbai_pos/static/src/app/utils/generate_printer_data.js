import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/generate_printer_data";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    generateData() {
        const data = super.generateData(...arguments);
        const url = this.order.uiState.l10n_es_pos_tbai_qrsrc;

        if (url) {
            data.image.l10n_es_pos_tbai_qrsrc = this.generateQrCode(url);
        }

        return data;
    },
});
