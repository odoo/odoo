import { _t } from "@web/core/l10n/translation";

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
