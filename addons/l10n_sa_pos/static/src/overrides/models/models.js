/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        if (this.pos.company.country && this.pos.company.country.code === "SA") {
            result.is_settlement = this.is_settlement();
            if (!result.is_settlement) {
                const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
                const qr_values = this.compute_sa_qr_code(
                    result.company.name,
                    result.company.vat,
                    result.date.isostring,
                    result.total_with_tax,
                    result.total_tax
                );
                const qr_code_svg = new XMLSerializer().serializeToString(
                    codeWriter.write(qr_values, 150, 150)
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
            !!this.paymentlines.filter(
                (paymentline) =>
                    paymentline.payment_method.type === "pay_later" && paymentline.amount < 0
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
});
