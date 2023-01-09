/** @odoo-module */

/**
 * Requires to have the file o_spreadsheet.d.ts included in the file tsconfig.json
 * See https://github.com/odoo/odoo/blob/16.0/addons/web/tooling/types/readme.md
 */
/** @type {o_spreadsheet} */
const spreadsheet = window.o_spreadsheet;
export const initCallbackRegistry = new spreadsheet.Registry();

import { _t } from "@web/core/l10n/translation";
spreadsheet.setTranslationMethod(_t);

// export * from spreadsheet ?
export default spreadsheet;
