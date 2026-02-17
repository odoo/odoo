import { isTableCell } from "./dom_info";
import { closestElement } from "./dom_traversal";

/**
 * Get the index of the given table row/cell.
 *
 * @private
 * @param {HTMLTableRowElement|HTMLTableCellElement} trOrTd
 * @returns {number}
 */
export function getRowIndex(trOrTd) {
    const tr = closestElement(trOrTd, "tr");
    return tr.rowIndex;
}

/**
 * Get the index of the given table cell.
 *
 * @private
 * @param {HTMLTableCellElement} td
 * @returns {number}
 */
export function getColumnIndex(td) {
    return td.cellIndex;
}

/**
 * Get all the cells of given table
 * (excluding nested table cells).
 *
 * @param {HTMLTableElement} table
 * @returns {Array<HTMLTableCellElement>}
 */
export function getTableCells(table) {
    return [...table.querySelectorAll("td, th")].filter(
        (cell) => closestElement(cell, "table") === table
    );
}

/**
 * Analyzes the currently selected table cells and determines:
 *  - whether they can be merged,
 *  - whether they can be unmerged,
 *  - and along which span type (`rowSpan` or `colSpan`) a merge is possible.
 *
 * @param {Document} editableDocument
 * @param {HTMLTableCellElement[][]} tableGrid
 * @param {HTMLTableCellElement} targetCell
 * The table cell currently hovered by the mouse.
 * @returns {Object} An object with the following properties:
 *   - {boolean} canMerge - True if selected cells can be merged.
 *   - {boolean} canUnmerge
 *     True if the anchor or selected table cell has rowSpan or colSpan > 1.
 *   - {Array<HTMLTableCellElement>} selectedCells - The selected cells.
 *   - {"colSpan" | "rowSpan" | ""} spanType - The span type along which
 *     the cells can be merged, or an empty string if merging is not possible.
 */
export function getSelectedCellsMergeInfo(editableDocument, tableGrid, targetCell) {
    const selectedTds = Array.from(editableDocument.querySelectorAll(".o_selected_td"));
    if (selectedTds.length <= 1) {
        const { anchorNode } = editableDocument.getSelection();
        const td = selectedTds[0] ?? (anchorNode && closestElement(anchorNode, isTableCell));
        return {
            canMerge: false,
            canUnmerge: td?.rowSpan > 1 || td?.colSpan > 1,
            cells: [],
            spanType: "",
        };
    }

    const firstCell = selectedTds[0];
    const lastCell = selectedTds[selectedTds.length - 1];

    const table = closestElement(firstCell, "table");
    const isSameTable =
        table &&
        table === closestElement(lastCell, "table") &&
        table === closestElement(targetCell, "table");

    if (!isSameTable) {
        return { canMerge: false, canUnmerge: false, cells: [], spanType: "" };
    }

    const getGridColumnIndex = (cell, row) => tableGrid[row].indexOf(cell);

    const rowIndexes = selectedTds.map(getRowIndex);
    const colIndexes = selectedTds.map((td, i) => getGridColumnIndex(td, rowIndexes[i]));

    const referenceRowIndex = rowIndexes[0];
    const referenceColIndex = colIndexes[0];

    const allInSameRow = rowIndexes.every((r) => r === referenceRowIndex);
    const allInSameCol = colIndexes.every((c) => c === referenceColIndex);
    const containsMergedCell = selectedTds.some((td) => td.rowSpan > 1 || td.colSpan > 1);
    // All in same row + no rowspan
    if (allInSameRow && selectedTds.every((td) => !td.hasAttribute("rowspan"))) {
        return {
            canMerge: true,
            canUnmerge: containsMergedCell,
            cells: selectedTds,
            spanType: "colSpan",
        };
    }

    // All in same col + no colspan
    if (allInSameCol && selectedTds.every((td) => !td.hasAttribute("colspan"))) {
        return {
            canMerge: true,
            canUnmerge: containsMergedCell,
            cells: selectedTds,
            spanType: "rowSpan",
        };
    }

    return { canMerge: false, canUnmerge: containsMergedCell, cells: selectedTds, spanType: "" };
}
