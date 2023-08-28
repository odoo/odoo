/** @odoo-module */

import { loadJS } from "@web/core/assets";

/**
 * Load external libraries required for o-spreadsheet
 * @returns {Promise<void>}
 */
export async function loadSpreadsheetDependencies() {
    await loadJS("/web/static/lib/Chart/Chart.js");
    await loadJS("/web/static/lib/chartjs-adapter-luxon/chartjs-adapter-luxon.js");
}
