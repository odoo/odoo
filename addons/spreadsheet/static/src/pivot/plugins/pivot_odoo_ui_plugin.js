/** @odoo-module */

import { OdooUIPlugin } from "@spreadsheet/plugins";
import { helpers, constants, SpreadsheetPivotTable } from "@odoo/o-spreadsheet";
const { PIVOT_TABLE_CONFIG } = constants;

const { UNDO_REDO_PIVOT_COMMANDS } = helpers;
UNDO_REDO_PIVOT_COMMANDS.push("UPDATE_ODOO_PIVOT_DOMAIN");

export class PivotOdooUIPlugin extends OdooUIPlugin {
    static getters = /** @type {const} */ ([]);

    /**
     * Handle a spreadsheet command
     * @param {Object} cmd Command
     */
    handle(cmd) {
        switch (cmd.type) {
            case "REFRESH_ALL_DATA_SOURCES":
                this.refreshAllPivots();
                break;
            case "INSERT_ODOO_FIX_PIVOT": {
                const { cols, rows, measures, rowTitle } = cmd.table;
                const table = new SpreadsheetPivotTable(cols, rows, measures, rowTitle);
                this.insertOdooFixPivot(cmd.pivotId, cmd.position, table);
                break;
            }
        }
    }

    /**
     * Refresh the cache of all the pivots
     */
    refreshAllPivots() {
        for (const pivotId of this.getters.getPivotIds()) {
            this.dispatch("REFRESH_PIVOT", { id: pivotId });
        }
    }

    insertOdooFixPivot(pivotId, position, table) {
        this.dispatch("INSERT_PIVOT", {
            ...position,
            pivotId,
            table: table.export(),
        });
        this.insertTableOnPivot(position, table);
    }

    insertTableOnPivot(position, table) {
        const pivotCells = table.getPivotCells();
        const pivotZone = {
            top: position.row,
            bottom: position.row + pivotCells[0].length - 1,
            left: position.col,
            right: position.col + pivotCells.length - 1,
        };
        const numberOfHeaders = table.columns.length - 1;
        const cmdContent = {
            sheetId: position.sheetId,
            ranges: [this.getters.getRangeDataFromZone(position.sheetId, pivotZone)],
            config: { ...PIVOT_TABLE_CONFIG, numberOfHeaders },
            tableType: "static",
        };
        this.dispatch("CREATE_TABLE", cmdContent);
    }
}
