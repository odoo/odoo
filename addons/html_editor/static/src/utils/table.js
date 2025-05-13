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
 * Analyzes selected table cells to determine if they can be merged and which
 * merge direction(s) (rowspan or colspan) are applicable.
 *
 * @param {Document} editableDocument
 * @param {HTMLTableCellElement[][]} tableGrid
 * @returns {Object} An object with the following properties:
 *   - {boolean} canMerge - True if selection can be merged.
 *   - {Array<HTMLTableCellElement>} selectedCells - The selected cells.
 *   - {"colSpan" | "rowSpan" | ""} direction - Merge direction.
 */
export function getSelectedCellsMergeInfo(editableDocument, tableGrid) {
    const selectedTds = Array.from(editableDocument.querySelectorAll(".o_selected_td"));
    const firstTd = selectedTds[0];
    const lastTd = selectedTds[selectedTds.length - 1];
    if (
        selectedTds.length <= 1 ||
        closestElement(firstTd, "table") !== closestElement(lastTd, "table")
    ) {
        return { cenMerge: false, cells: [], direction: "" };
    }

    const getGridColumnIndex = (cell, row) => tableGrid[row].indexOf(cell);

    const rowIndexes = selectedTds.map(getRowIndex);
    const colIndexes = selectedTds.map((td, i) => getGridColumnIndex(td, rowIndexes[i]));

    const referenceRowIndex = rowIndexes[0];
    const referenceColIndex = colIndexes[0];

    const allInSameRow = rowIndexes.every((r) => r === referenceRowIndex);
    const allInSameCol = colIndexes.every((c) => c === referenceColIndex);

    // All in same row + no rowspan
    if (allInSameRow && selectedTds.every((td) => !td.hasAttribute("rowspan"))) {
        return { canMerge: true, cells: selectedTds, direction: "colSpan" };
    }

    // All in same col + no colspan
    if (allInSameCol && selectedTds.every((td) => !td.hasAttribute("colspan"))) {
        return { canMerge: true, cells: selectedTds, direction: "rowSpan" };
    }

    return { canMerge: false, cells: [], direction: "" };
}
