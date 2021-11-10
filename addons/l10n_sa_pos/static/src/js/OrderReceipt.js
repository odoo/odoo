odoo.define('l10n_sa_pos.OrderReceipt', function (require) {
    'use strict';

    const OrderReceipt = require('point_of_sale.OrderReceipt')
    const Registries = require('point_of_sale.Registries');

    const OrderReceiptQRCodeSA = OrderReceipt =>
        class extends OrderReceipt {
            mounted() {
                super.mounted(...arguments);
                if (this._receiptEnv.order.pos.company.country.code === 'SA') {
                    const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter()
                    codeWriter.writeToDom('#qrcode', this._receiptEnv.receipt.qr_code, 150, 150);
                }
            }

            get receiptEnv() {
                if (this._receiptEnv.order.pos.company.country.code === 'SA') {
                    let receipt_render_env = super.receiptEnv;
                    let receipt = receipt_render_env.receipt;
                    receipt.qr_code = this.compute_sa_qr_code(receipt.company.name, receipt.company.vat, receipt.date.isostring, receipt.total_with_tax, receipt.total_tax);
                    return receipt_render_env;
                }
                return super.receiptEnv;
            }

            compute_sa_qr_code(name, vat, date_isostring, amount_total, amount_tax) {
                /* Generate the qr code for Saudi e-invoicing. Specs are available at the following link at page 23
                https://zatca.gov.sa/ar/E-Invoicing/SystemsDevelopers/Documents/20210528_ZATCA_Electronic_Invoice_Security_Features_Implementation_Standards_vShared.pdf
                */
                const seller_name_enc = this._compute_qr_code_field(1, name);
                const company_vat_enc = this._compute_qr_code_field(2, vat);
                const timestamp_enc = this._compute_qr_code_field(3, date_isostring);
                const invoice_total_enc = this._compute_qr_code_field(4, amount_total.toString());
                const total_vat_enc = this._compute_qr_code_field(5, amount_tax.toString());

                const str_to_encode = seller_name_enc.concat(company_vat_enc, timestamp_enc, invoice_total_enc, total_vat_enc);

                let binary = '';
                for (let i = 0; i < str_to_encode.length; i++) {
                    binary += String.fromCharCode(str_to_encode[i]);
                }
                return btoa(binary);
            }

            _compute_qr_code_field(tag, field) {
                const textEncoder = new TextEncoder();
                const name_byte_array = Array.from(textEncoder.encode(field));
                const name_tag_encoding = [tag];
                const name_length_encoding = [name_byte_array.length];
                return name_tag_encoding.concat(name_length_encoding, name_byte_array);
            }
        }
    Registries.Component.extend(OrderReceipt, OrderReceiptQRCodeSA)
    return OrderReceiptQRCodeSA
});
