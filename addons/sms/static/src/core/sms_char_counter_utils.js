/** @odoo-module **/

export const GSM7_MAX_CHAR = 160;
export const GSM7_CONCATENATED_MAX_CHAR = 153;

export const UCS2_MAX_CHAR = 70;
export const UCS2_CONCATENATED_MAX_CHAR = 67;

export function countSMS(nbrChar, encoding) {
    if (nbrChar === 0) return 0;
    if (encoding === 'UNICODE') {
        return nbrChar <= UCS2_MAX_CHAR ? 1 : Math.ceil(nbrChar / UCS2_CONCATENATED_MAX_CHAR);
    }
    return nbrChar <= GSM7_MAX_CHAR ? 1 : Math.ceil(nbrChar / GSM7_CONCATENATED_MAX_CHAR);
}

export function extractSmsEncoding(content) {
    if (String(content).match(RegExp("^[@£$¥èéùìòÇ\\nØø\\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\\\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà]*$"))) {
        return 'GSM7';
    }
    return 'UNICODE';
}
