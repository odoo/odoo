/** @odoo-module **/

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
};
