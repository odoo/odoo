/** @odoo-module **/

/**
 * @type {any}
 */
const notReadyError = new Error(
  "Localization parameters not ready yet. Maybe add 'localization' to your dependencies?"
);

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
