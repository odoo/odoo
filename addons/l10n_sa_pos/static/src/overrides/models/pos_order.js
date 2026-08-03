import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { computeSAQRCode, renderQRCodeDataURL } from "@l10n_sa_pos/app/utils/qr";

patch(PosOrder.prototype, {
    generateQrcode() {
        if (this.company.country_id?.code === "SA") {
            if (!this.is_settlement()) {
                const company = this.company;
                const qr_values = this.compute_sa_qr_code(
                    company.name,
                    company.vat,
                    this.date_order,
                    this.getTotalWithTax(),
                    this.getTotalTax()
                );
                return renderQRCodeDataURL(qr_values, 200);
            }
        }
        return false;
    },
    /**
     * If the module pos_settle_due is not installed,
     * the function always returns false (since "isAnySettleLine" doesn't exist)
     * @returns {boolean} true if the current order is a settlement or deposit, else false
     */
    is_settlement() {
        return this.lines.some((line) => line.isAnySettleLine?.());
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
