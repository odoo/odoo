import { deserializeDateTime, formatDateTime } from "@web/core/l10n/dates";

export function computeSAQRCode(name, vat, date_isostring, amount_total, amount_tax) {
    /* Generate the qr code for Saudi e-invoicing. Specs are available at the following link at page 23
    https://zatca.gov.sa/ar/E-Invoicing/SystemsDevelopers/Documents/20210528_ZATCA_Electronic_Invoice_Security_Features_Implementation_Standards_vShared.pdf
    */

    const ksa_timestamp = formatDateTime(deserializeDateTime(date_isostring), {
        tz: "Asia/Riyadh",
        format: "MM/dd/yyyy, HH:mm:ss",
    });

    const seller_name_enc = _compute_qr_code_field(1, name);
    const company_vat_enc = _compute_qr_code_field(2, vat);
    const timestamp_enc = _compute_qr_code_field(3, ksa_timestamp);
    const invoice_total_enc = _compute_qr_code_field(4, amount_total.toString());
    const total_vat_enc = _compute_qr_code_field(5, amount_tax.toString());

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
}
function _compute_qr_code_field(tag, field) {
    const textEncoder = new TextEncoder();
    const name_byte_array = Array.from(textEncoder.encode(field));
    const name_tag_encoding = [tag];
    const name_length_encoding = [name_byte_array.length];
    return name_tag_encoding.concat(name_length_encoding, name_byte_array);
}
