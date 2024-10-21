/** @odoo-module */

import { loadBundle, loadJS } from "@web/core/assets";

/**
 * Load external libraries required for o-spreadsheet
 * @returns {Promise<void>}
 */
export async function loadSpreadsheetDependencies() {
    await loadBundle("web.chartjs_lib");
    await loadJS("/web/static/lib/chartjs-chart-geo/chartjs-chart-geo.js");
}
