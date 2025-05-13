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
    return [...table.querySelectorAll("td")].filter((td) => closestElement(td, "table") === table);
}

/**
 * Analyzes selected table cells to determine if they can be merged and which
 * merge direction(s) (rowspan or colspan) are applicable.
 *
 * @param {HTMLElement} editable
 * @returns {[false, false] | [Array<HTMLTableCellElement>, "rowspan" | "colspan"]}
 *   - [false, false] if merging is not possible (only one cell selected or are already merged),
 *   - Otherwise, returns the selected cells and applicable span(s).
 */
export function getSelectedCellsMergeInfo(editable) {
    const selectedTds = Array.from(editable.querySelectorAll(".o_selected_td"));
    const { anchorNode, focusNode } = editable.getSelection();
    if (
        selectedTds.length <= 1 ||
        closestElement(anchorNode, "table") !== closestElement(focusNode, "table") ||
        selectedTds.some((td) => td.rowSpan > 1 || td.colSpan > 1)
    ) {
        return [false, false];
    }

    const firstTd = selectedTds[0];
    const firstRowIndex = getRowIndex(firstTd);
    const spansToApply = new Set(["rowspan", "colspan"]);

    for (let i = 1; i < selectedTds.length; i++) {
        const rowIndex = getRowIndex(selectedTds[i]);
        rowIndex !== firstRowIndex
            ? spansToApply.delete("colspan")
            : spansToApply.delete("rowspan");
        if (!spansToApply.size) {
            break;
        }
    }
    return [selectedTds, ...spansToApply];
}
