/** @odoo-module */

const spreadsheet = window.o_spreadsheet;
export const initCallbackRegistry = new spreadsheet.Registry();

import { _t } from "@web/core/l10n/translation";
spreadsheet.setTranslationMethod(_t);

// export * from spreadsheet ?
export default spreadsheet;
