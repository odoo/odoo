import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { computeSAQRCode } from "@l10n_sa_pos/app/utils/qr";

patch(PosOrder.prototype, {
    isSACompany() {
        return this.company.country_id?.code === "SA";
    },

    generateQrcode() {
        if (this.isSACompany()) {
            if (!this.isSettlement()) {
                const company = this.company;
                const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
                const qr_values = this.compute_sa_qr_code(
                    company.name,
                    company.vat,
                    this.date_order,
                    this.priceIncl,
                    this.amountTaxes
                );
                const qr_code_svg = new XMLSerializer().serializeToString(
                    codeWriter.write(qr_values, 200, 200)
                );
                return "data:image/svg+xml;base64," + window.btoa(qr_code_svg);
            }
        }
        return false;
    },
    compute_sa_qr_code(name, vat, date_isostring, amount_total, amount_tax) {
        return computeSAQRCode(name, vat, date_isostring, amount_total, amount_tax);
    },
    get isSimplified() {
        return !this?.partner_id?.is_company && this.company_id.country_id?.code === "SA";
    },
});
