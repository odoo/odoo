import { Registry } from "@odoo/o-spreadsheet";
import { SpreadsheetPivotTable } from "../pivot_table";

/**
 * @typedef {import("@spreadsheet").OdooInsertPivotPayload} OdooInsertPivotPayload
 * @typedef {import("@spreadsheet").SpreadsheetInsertPivotPayload} SpreadsheetInsertPivotPayload
 * @typedef {import("@spreadsheet").PivotHandler} PivotHandler
 */

/**
 * @type {Registry<PivotHandler>}
 */
export const pivotRegistry = new Registry();

pivotRegistry.add("ODOO", {
    /**
     * @param {OdooInsertPivotPayload} payload
     * @returns {SpreadsheetPivotTable}
     */
    getTable(payload) {
        const { cols, rows, measures, rowTitle } = payload.table;
        return new SpreadsheetPivotTable(cols, rows, measures, rowTitle);
    },
});

pivotRegistry.add("SPREADSHEET", {
    /**
     * @param {SpreadsheetInsertPivotPayload} payload
     * @returns {SpreadsheetPivotTable}
     */
    getTable() {
        return new SpreadsheetPivotTable([[]], [], []);
    },
});
