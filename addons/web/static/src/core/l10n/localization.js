/** @odoo-module **/

/**
 * @type {any}
 */
const notReadyError = new Error(
    "Localization parameters not ready yet. Maybe add 'localization' to your dependencies?"
);

export const localization = {
    code: notReadyError,
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
