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
