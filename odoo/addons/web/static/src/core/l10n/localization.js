/** @odoo-module **/

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
 * @type {any}
 */
const notReadyError = new Error(
    "Localization parameters not ready yet. Maybe add 'localization' to your dependencies?"
);

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
export const localization = {
    dateFormat: notReadyError,
    dateTimeFormat: notReadyError,
    timeFormat: notReadyError,
    decimalPoint: notReadyError,
    direction: notReadyError,
    grouping: notReadyError,
    multiLang: notReadyError,
    thousandsSep: notReadyError,
    weekStart: notReadyError,
    code: notReadyError,
};
