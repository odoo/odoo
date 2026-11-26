import { _t } from "@web/core/l10n/translation";
import { localizeDigits } from "@web/core/l10n/numbering";

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
    return localizeDigits(`${i === 0 ? size : size.toFixed(2)} ${units[i].trim()}`);
}
