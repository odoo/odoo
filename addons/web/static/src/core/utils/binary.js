import { _t } from "@web/core/l10n/translation";

/**
 * @param {string} value
 * @returns {boolean}
 */
export function isBinarySize(value) {
    return /^\d+(\.\d*)? [^0-9]+$/.test(value);
}

/**
 * @param {number} size number of bytes
 * @param {string}
 */
export function humanSize(size) {
    const units = _t("Bytes|kB|MB|GB|TB|PB|EB|ZB|YB").split("|");
    let i = 0;
    while (size >= 1024) {
        size /= 1024;
        ++i;
    }
    return `${i === 0 ? size : size.toFixed(2)} ${units[i].trim()}`;
}
