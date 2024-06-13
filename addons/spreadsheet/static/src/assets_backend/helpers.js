/** @odoo-module */

import { loadBundle } from "@web/core/assets";

/**
 * Load external libraries required for o-spreadsheet
 * @returns {Promise<void>}
 */
export async function loadSpreadsheetDependencies() {
    await loadBundle("web.chartjs_lib");
}
