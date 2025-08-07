import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

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
     * If the order is empty (there are no products)
     * and all "pay_later" payments are negative,
     * we are settling a customer's account.
     * If the module pos_settle_due is not installed,
     * the function always returns false (since "pay_later" doesn't exist)
     * @returns {boolean} true if the current order is a settlement, else false
     */
    is_settlement() {
        return (
            this.isEmpty() &&
            !!this.payment_ids.filter(
                (paymentline) =>
                    paymentline.payment_method_id.type === "pay_later" && paymentline.amount < 0
            ).length
        );
    },
    compute_sa_qr_code(name, vat, date_isostring, amount_total, amount_tax) {
        /* Generate the qr code for Saudi e-invoicing. Specs are available at the following link at page 23
https://zatca.gov.sa/ar/E-Invoicing/SystemsDevelopers/Documents/20210528_ZATCA_Electronic_Invoice_Security_Features_Implementation_Standards_vShared.pdf
*/
        const seller_name_enc = this._compute_qr_code_field(1, name);
        const company_vat_enc = this._compute_qr_code_field(2, vat);
        const timestamp_enc = this._compute_qr_code_field(3, date_isostring);
        const invoice_total_enc = this._compute_qr_code_field(4, amount_total.toString());
        const total_vat_enc = this._compute_qr_code_field(5, amount_tax.toString());

        const str_to_encode = seller_name_enc.concat(
            company_vat_enc,
            timestamp_enc,
            invoice_total_enc,
            total_vat_enc
        );

        let binary = "";
        for (let i = 0; i < str_to_encode.length; i++) {
            binary += String.fromCharCode(str_to_encode[i]);
        }
        return btoa(binary);
    },
    _compute_qr_code_field(tag, field) {
        const textEncoder = new TextEncoder();
        const name_byte_array = Array.from(textEncoder.encode(field));
        const name_tag_encoding = [tag];
        const name_length_encoding = [name_byte_array.length];
        return name_tag_encoding.concat(name_length_encoding, name_byte_array);
    },
    get isSimplified() {
        return (
            (this?.partner_id?.company_type === "person" || !this?.partner_id) &&
            this.company_id.country_id?.code === "SA"
        );
    },
});
