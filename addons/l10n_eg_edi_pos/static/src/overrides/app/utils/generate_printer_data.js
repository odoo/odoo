import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";
import { patch } from "@web/core/utils/patch";
import { generateQRCodeDataUrl } from "@point_of_sale/utils";

patch(GeneratePrinterData.prototype, {
    generateReceiptData() {
        const data = super.generateReceiptData(...arguments);
        if (
            this.order.company.account_fiscal_country_id?.code === "EG" &&
            this.order.l10n_eg_edi_pos_qr
        ) {
            data.extra_data.l10n_eg_edi_pos_qr = generateQRCodeDataUrl(
                this.order.l10n_eg_edi_pos_qr
            );
        }
        return data;
    },
});
