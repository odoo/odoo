// @ts-check
/** @odoo-module native */

const FA_STYLE_PREFIXES = ["fa-solid", "fa-regular", "fa-brands"];

/**
 * Font Awesome 7 draws nothing for a glyph class without a style class, so a
 * bare `fa-clipboard` — the FA4 spelling every arch attribute and most
 * callers still use — is completed to `fa-solid fa-clipboard`; the FA4 `fa `
 * base is dropped on the way. A class that already names its style is kept.
 *
 * @param {string} iconClass
 * @returns {string}
 */
export function faIconClass(iconClass) {
    if (FA_STYLE_PREFIXES.some((prefix) => iconClass.startsWith(prefix))) {
        return iconClass;
    }
    const glyph = iconClass.startsWith("fa fa-") ? iconClass.slice(3) : iconClass;
    return `fa-solid ${glyph}`;
}
