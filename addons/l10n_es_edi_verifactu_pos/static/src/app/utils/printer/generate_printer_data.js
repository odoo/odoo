import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    generateReceiptData() {
        const data = super.generateReceiptData(...arguments);

        if (this.company.l10n_es_edi_verifactu_required) {
            data.conditions.display_vat = !this.order.account_move;
        }

        if (this.order.l10n_es_edi_verifactu_qr_code) {
            data.image.l10n_es_edi_verifactu_qr_code = this.generateQrCode(
                this.order.l10n_es_edi_verifactu_qr_code
            );
            data.conditions.l10n_es_edi_verifactu_pos = true;
            data.conditions.has_account_move = Boolean(this.order.account_move);
            data.extra_data.invoice_name = this.order.account_move?.name || "";
        }

        return data;
    },
});
