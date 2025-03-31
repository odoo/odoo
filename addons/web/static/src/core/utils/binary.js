import { _t } from "@web/core/l10n/translation";

/**
 * @param {string} value
 * @returns {boolean}
 */
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

/**
 * @param {number} size number of bytes
 * @param {string}
 */
export function humanSize(size) {
    const units = _t("Bytes|Kb|Mb|Gb|Tb|Pb|Eb|Zb|Yb").split("|");
    let i = 0;
    while (size >= 1024) {
        size /= 1024;
        ++i;
    }
    return `${size.toFixed(2)} ${units[i].trim()}`;
}
