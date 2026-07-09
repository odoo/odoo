import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";
import { patch } from "@web/core/utils/patch";
import { qrCodeSrc } from "@point_of_sale/utils";

patch(GeneratePrinterData.prototype, {
    generateReceiptData() {
        const data = super.generateReceiptData(...arguments);
        if (this.order.company.country_id?.code === "PK" && this.order.l10n_pk_edi_pos_qr) {
            data.extra_data.l10n_pk_edi_pos_qr = qrCodeSrc(this.order.l10n_pk_edi_pos_qr);
        }
        return data;
    },
});
