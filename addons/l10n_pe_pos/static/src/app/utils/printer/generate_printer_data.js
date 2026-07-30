import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";

patch(GeneratePrinterData.prototype, {
    generateReceiptData() {
        const data = super.generateReceiptData(...arguments);
        if (this.company.account_fiscal_country_id?.code == "PE") {
            data.extra_data.partner_vat_label =
                this.order.partner_id?.l10n_latam_identification_type_id?.name;
        }
        return data;
    },
});
