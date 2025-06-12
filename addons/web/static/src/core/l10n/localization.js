/**
 * @typedef Localization
 * @property {string} dateFormat
 * @property {string} dateTimeFormat
 * @property {string} timeFormat
 * @property {string} decimalPoint
 * @property {"ltr" | "rtl"} direction
 * @property {[number, number]} grouping
 * @property {boolean} multiLang
 * @property {string} thousandsSep
 * @property {number} weekStart
 * @property {string} code
 */

/**
 * This is the main object holding user specific data about the localization. Its basically
 * the JS counterpart of the "res.lang" model.
 * It is useful to directly access those data anywhere, even outside Components.
 *
 * Important Note: its data are actually loaded by the localization_service,
 * so a code like the following would not work:
 *   import { localization } from "@web/core/l10n/localization";
 *   const dateFormat = localization.dateFormat; // dateFormat isn't set yet
 * @type {Localization}
 */
export const localization = new Proxy(
    {},
    {
        get: (target, p) => {
            // "then" can be called implicitly if the object is returned in an
            // `async` function, so we need to allow it.
            if (p in target || p === "then") {
                return Reflect.get(target, p);
            }
            throw new Error(
                `could not access localization parameter "${p}": parameters are not ready yet. Maybe add 'localization' to your dependencies?`
            );
        },
    }
);
