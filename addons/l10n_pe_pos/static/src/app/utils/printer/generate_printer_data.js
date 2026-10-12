import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";

patch(GeneratePrinterData.prototype, {
    generateReceiptData() {
        const data = super.generateReceiptData(...arguments);
        const partner = this.order.partner_id;
        if (this.company.account_fiscal_country_id?.code !== "PE" || !partner) {
            return data;
        }
        const metadata = partner.available_additional_identifiers_metadata || {};
        const identifiers = Object.entries(partner.additional_identifiers || {});
        if (partner.vat) {
            // the RUC, kept in the vat, outranks the additional identifiers
            identifiers.unshift(["PE_RUC", partner.vat]);
        }
        const [key, value] =
            identifiers.sort(
                ([a], [b]) => (metadata[a]?.sequence ?? 100) - (metadata[b]?.sequence ?? 100)
            )[0] || [];
        if (value) {
            data.partner = { ...data.partner, vat: value };
            if (metadata[key]?.label) {
                data.extra_data.partner_vat_label = metadata[key].label;
            }
        }
        return data;
    },
});
