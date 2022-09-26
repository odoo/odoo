/** @odoo-module */

import { getNumberOfListFormulas } from "@spreadsheet/list/list_helpers";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { getNumberOfPivotFormulas } from "@spreadsheet/pivot/pivot_helpers";
import { patch } from "@web/core/utils/patch";

const { Grid } = spreadsheet.components;

function positionToZone(position) {
    return { left: position.col, right: position.col, top: position.row, bottom: position.row };
}

/**
 * @typedef ClickableCell
 * @property {number} left Left position of the cell
 * @property {number} top Top position of the cell
 * @property {number} width Width of the cell
 * @property {number} height Height of the cell
 * @property {number} key Unique identifier
 */

/* Used for t-key */
let key = 0;

patch(Grid.prototype, "spreadsheet_dashboard_grid_cursor", {
    getCellClickableStyle(coordinates) {
        return `
      top: ${coordinates.top}px;
      left: ${coordinates.left}px;
      width: ${coordinates.width}px;
      height: ${coordinates.height}px;
    `;
    },

    /**
     * Get all the boxes for the cell in the sheet view that are clickable.
     * This function is used to render an overlay over each clickable cell in
     * order to display a pointer cursor.
     *
     * @returns {Array<ClickableCell>}
     */
    getClickableCells() {
        const cells = [];
        const sheetId = this.env.model.getters.getActiveSheetId();
        for (const col of this.env.model.getters.getSheetViewVisibleCols()) {
            for (const row of this.env.model.getters.getSheetViewVisibleRows()) {
                const cell = this.env.model.getters.getCell(sheetId, col, row);
                if (this.isClickable(cell)) {
                    let zone;
                    if (this.env.model.getters.isInMerge(sheetId, col, row)) {
                        zone = this.env.model.getters.getMerge(sheetId, col, row);
                    } else {
                        zone = positionToZone({ col, row });
                    }
                    const rect = this.env.model.getters.getVisibleRect(zone);
                    cells.push({
                        left: rect.x,
                        top: rect.y,
                        width: rect.width,
                        height: rect.height,
                        key: ++key,
                    });
                }
            }
        }
        return cells;
    },

    isClickable(cell) {
        if (!cell) {
            return false;
        }
        // Links
        if (cell.isLink()) {
            return true;
        }
        // Pivot / Lists
        if (
            cell.isFormula() &&
            cell.evaluated.value !== "" &&
            !cell.evaluated.error &&
            (getNumberOfPivotFormulas(cell.content) === 1 ||
                getNumberOfListFormulas(cell.content) === 1)
        ) {
            return true;
        }
        return false;
    },
});
