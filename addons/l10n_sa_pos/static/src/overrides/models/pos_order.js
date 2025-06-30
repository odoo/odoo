import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { computeSAQRCode } from "@l10n_sa_pos/app/utils/qr";

patch(PosOrder.prototype, {
    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(...arguments);
        if (this.company.country_id?.code === "SA") {
            result.is_settlement = this.is_settlement();
            if (!result.is_settlement) {
                const company = this.company;
                const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
                const qr_values = this.compute_sa_qr_code(
                    company.name,
                    company.vat,
                    this.date_order,
                    this.get_total_with_tax(),
                    this.get_total_tax()
                );
                const qr_code_svg = new XMLSerializer().serializeToString(
                    codeWriter.write(qr_values, 200, 200)
                );
                result.qr_code = "data:image/svg+xml;base64," + window.btoa(qr_code_svg);
            }
        }
        return result;
    },
    /**
     * If the order is empty (there are no products)
     * and all "pay_later" payments are negative,
     * we are settling a customer's account.
     * If the module pos_settle_due is not installed,
     * the function always returns false (since "pay_later" doesn't exist)
     * @returns {boolean} true if the current order is a settlement, else false
     */
    is_settlement() {
        return (
            this.is_empty() &&
            !!this.payment_ids.filter(
                (paymentline) =>
                    paymentline.payment_method_id.type === "pay_later" && paymentline.amount < 0
            ).length
        );
    },

    compute_sa_qr_code(name, vat, date_isostring, amount_total, amount_tax) {
        return computeSAQRCode(name, vat, date_isostring, amount_total, amount_tax);
    },
});
