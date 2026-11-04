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
/**
 * Render `values` as a `size`x`size` QR code, as an SVG data URL.
 *
 * ZXing draws each module at a whole number of pixels of the canvas it is given, so a
 * fixed canvas keeps a leftover margin that depends on how many modules the payload
 * needs: the longer the seller name encoded in the ZATCA TLV payload, the more modules,
 * and the smaller the code drawn in the same box. Rendering at the code's natural size
 * (one unit per module, no leftover) and scaling through a viewBox instead keeps the
 * code the same size whatever the payload length.
 */
export function renderQRCodeDataURL(values, size) {
    // A canvas of 0 makes the writer fall back to the code's natural size.
    const svg = new window.ZXing.BrowserQRCodeSvgWriter().write(values, 0, 0);
    svg.setAttribute("viewBox", `0 0 ${svg.getAttribute("width")} ${svg.getAttribute("height")}`);
    svg.setAttribute("width", size);
    svg.setAttribute("height", size);
    // The viewBox scales the modules to a fractional size; don't blur their edges.
    svg.setAttribute("shape-rendering", "crispEdges");
    return "data:image/svg+xml;base64," + btoa(new XMLSerializer().serializeToString(svg));
}

function _compute_qr_code_field(tag, field) {
    const textEncoder = new TextEncoder();
    const name_byte_array = Array.from(textEncoder.encode(field));
    const name_tag_encoding = [tag];
    const name_length_encoding = [name_byte_array.length];
    return name_tag_encoding.concat(name_length_encoding, name_byte_array);
}
