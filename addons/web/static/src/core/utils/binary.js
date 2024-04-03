/** @odoo-module **/

export function isBinarySize(value) {
    return /^\d+(\.\d*)? [^0-9]+$/.test(value);
}

/**
 * Get the length necessary for a base64 str to encode maxBytes
 * @param {number} maxBytes number of bytes we want to encode in base64
 * @returns {number} number of char
 */
export function toBase64Length(maxBytes) {
    return Math.ceil(maxBytes * 4 / 3);
}
