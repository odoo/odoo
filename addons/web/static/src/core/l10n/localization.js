// @ts-check
/** @odoo-module native */

/**
 * @typedef Localization
 * @property {string} dateFormat
 * @property {string} dateTimeFormat
 * @property {string} timeFormat
 * @property {string} decimalPoint
 * @property {"ltr" | "rtl"} direction
 * @property {number[]} grouping
 * @property {boolean} multiLang
 * @property {string | false} thousandsSep
 * @property {number} weekStart
 * @property {string} code
 * @property {string} translationsHash
 */

const ALLOWED_PROTOCOL_KEYS = new Set([
    "then",
    "toJSON",
    "constructor",
    "inspect",
    "destroy",
]);

/** @type {Localization} */
export const localization = new Proxy(/** @type {any} */ ({}), {
    get: (target, p) => {
        if (typeof p === "symbol" || p in target || ALLOWED_PROTOCOL_KEYS.has(p)) {
            return Reflect.get(target, p);
        }
        throw new Error(
            `could not access localization parameter "${String(p)}": parameters are not ready yet. Maybe add 'localization' to your dependencies?`,
        );
    },
});
