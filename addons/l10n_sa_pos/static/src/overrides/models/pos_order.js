import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { computeSAQRCode } from "@l10n_sa_pos/app/utils/qr";

patch(PosOrder.prototype, {
    generateQrcode() {
        if (this.company.country_id?.code === "SA") {
            if (!this.is_settlement()) {
                const company = this.company;
                const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
                const qr_values = this.compute_sa_qr_code(
                    company.name,
                    company.vat,
                    this.date_order,
                    this.getTotalWithTax(),
                    this.getTotalTax()
                );
                const qr_code_svg = new XMLSerializer().serializeToString(
                    codeWriter.write(qr_values, 200, 200)
                );
                return "data:image/svg+xml;base64," + window.btoa(qr_code_svg);
            }
        }
        return false;
    },
    /**
     * If the module pos_settle_due is not installed,
     * the function always returns false (since "isSettleDueLine" doesn't exist)
     * @returns {boolean} true if the current order is a settlement, else false
     */
    is_settlement() {
        return !!this.lines.filter((line) => line.isSettleDueLine?.()).length;
    },

    /**
     * Before validating the order, is_settling_account is set to True.
     * Once the order is validated and before sending the request to api,
     * is_settling_account property is not there anymore, thus checking lines
     * If the module pos_settle_due is not installed,
     * the function always returns false (since "isDepositLine or is_settling_account" doesn't exist)
     * @returns {boolean} true if the current order is a deposit, else false
     */
    is_deposit_order() {
        return (
            this.is_settling_account || !!this.lines.filter((line) => line.isDepositLine?.()).length
        );
    },

    compute_sa_qr_code(name, vat, date_isostring, amount_total, amount_tax) {
        return computeSAQRCode(name, vat, date_isostring, amount_total, amount_tax);
    },
    get isSimplified() {
        return (
            (this?.partner_id?.company_type === "person" || !this?.partner_id) &&
            this.company_id.country_id?.code === "SA"
        );
    },
});
