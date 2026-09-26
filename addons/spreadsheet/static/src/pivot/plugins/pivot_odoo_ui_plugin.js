import { OdooUIPlugin } from "@spreadsheet/plugins";
import { helpers } from "@odoo/o-spreadsheet";

const { UNDO_REDO_PIVOT_COMMANDS } = helpers;
UNDO_REDO_PIVOT_COMMANDS.push("UPDATE_ODOO_PIVOT_DOMAIN");

export class PivotOdooUIPlugin extends OdooUIPlugin {
    static getters = /** @type {const} */ ([]);

    handlers = {
        UPDATE_LOCALE: this.refreshAllPivots,
        REFRESH_ALL_DATA_SOURCES: this.refreshAllPivots,
    };

    /**
     * Refresh the cache of all the pivots
     */
    refreshAllPivots() {
        for (const pivotId of this.getters.getPivotIds()) {
            this.dispatch("REFRESH_PIVOT", { id: pivotId });
        }
    }
}
