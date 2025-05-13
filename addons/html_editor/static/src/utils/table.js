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
 * @param {Document} editableDocument
 * @returns {[false, false] | [Array<HTMLTableCellElement>, "rowspan" | "colspan"]}
 *   - [false, false] if merging is not possible (only one cell selected or are already merged),
 *   - Otherwise, returns the selected cells and applicable span(s).
 */
export function getSelectedCellsMergeInfo(editableDocument) {
    const selectedTds = Array.from(editableDocument.querySelectorAll(".o_selected_td"));
    const { anchorNode, focusNode } = editableDocument.getSelection();
    if (
        selectedTds.length <= 1 ||
        closestElement(anchorNode, "table") !== closestElement(focusNode, "table")
    ) {
        return [false, false];
    }

    const firstTd = selectedTds[0];
    const firstRowIndex = [getRowIndex(firstTd)];
    const spansToApply = new Set(["rowSpan", "colSpan"]);

    if (firstTd.rowSpan > 1) {
        spansToApply.delete("colSpan");
    } else if (firstTd.colSpan > 1) {
        spansToApply.delete("rowSpan");
    }

    for (let i = 1; i < selectedTds.length; i++) {
        const rowIndex = getRowIndex(selectedTds[i]);
        const sameRowIndex = firstRowIndex.includes(rowIndex);
        if (!sameRowIndex || selectedTds[i].rowSpan > 1) {
            spansToApply.delete("colSpan");
        }
        if (sameRowIndex || selectedTds[i].colSpan > 1) {
            spansToApply.delete("rowSpan");
        }
        firstRowIndex.push(rowIndex);
        if (!spansToApply.size) {
            break;
        }
    }
    return [selectedTds, ...spansToApply];
}
