import { Plugin } from "@html_editor/plugin";
import { isBlock } from "@html_editor/utils/blocks";
import { removeClass } from "@html_editor/utils/dom";
import { getDeepestPosition, isProtected, isProtecting } from "@html_editor/utils/dom_info";
import { ancestors, closestElement, descendants, lastLeaf } from "@html_editor/utils/dom_traversal";
import { parseHTML } from "@html_editor/utils/html";
import { DIRECTIONS, leftPos, rightPos } from "@html_editor/utils/position";
import { findInSelection } from "@html_editor/utils/selection";
import { getColumnIndex, getRowIndex } from "@html_editor/utils/table";

const tableInnerComponents = new Set(["THEAD", "TBODY", "TFOOT", "TR", "TH", "TD"]);
function isUnremovableTableComponent(element, root) {
    if (!tableInnerComponents.has(element.tagName)) {
        return false;
    }
    if (!root) {
        return true;
    }
    const closestTable = closestElement(element, "table");
    return !root.contains(closestTable);
}

/**
 * This plugin only contains the table manipulation and selection features. All UI overlay
 * code is located in the table_ui plugin
 */
export class TablePlugin extends Plugin {
    static name = "table";
    static dependencies = ["dom", "history", "selection", "delete", "split", "color"];
    /** @type { (p: TablePlugin) => Record<string, any> } */
    static resources = (p) => ({
        handle_tab: { callback: p.handleTab.bind(p), sequence: 20 },
        handle_shift_tab: { callback: p.handleShiftTab.bind(p), sequence: 20 },
        handle_delete_range: { callback: p.handleDeleteRange.bind(p) },
        isUnremovable: isUnremovableTableComponent,
        isUnsplittable: (element) =>
            element.tagName === "TABLE" || tableInnerComponents.has(element.tagName),
        onSelectionChange: p.updateSelectionTable.bind(p),
        colorApply: p.applyTableColor.bind(p),
        modifyTraversedNodes: p.adjustTraversedNodes.bind(p),
        considerNodeFullySelected: (node) => !!closestElement(node, ".o_selected_td"),
    });

    handleCommand(command, payload) {
        switch (command) {
            case "INSERT_TABLE":
                this.insertTable(payload);
                break;
            case "ADD_COLUMN":
                this.addColumn(payload);
                break;
            case "ADD_ROW":
                this.addRow(payload);
                break;
            case "REMOVE_COLUMN":
                this.removeColumn(payload);
                break;
            case "REMOVE_ROW":
                this.removeRow(payload);
                break;
            case "MOVE_COLUMN":
                this.moveColumn(payload);
                break;
            case "MOVE_ROW":
                this.moveRow(payload);
                break;
            case "RESET_SIZE":
                this.resetSize(payload);
                break;
            case "DELETE_TABLE":
                this.deleteTable(payload);
                break;
            case "CLEAN":
            case "CLEAN_FOR_SAVE":
                this.deselectTable(payload.root);
                break;
        }
    }

    handleTab() {
        const selection = this.shared.getEditableSelection();
        const inTable = closestElement(selection.anchorNode, "table");
        if (inTable) {
            // Move cursor to next cell.
            const shouldAddNewRow = !this.shiftCursorToTableCell(1);
            if (shouldAddNewRow) {
                this.addRow({ position: "after", reference: findInSelection(selection, "tr") });
                this.shiftCursorToTableCell(1);
                this.dispatch("ADD_STEP");
            }
            return true;
        }
    }

    handleShiftTab() {
        const selection = this.shared.getEditableSelection();
        const inTable = closestElement(selection.anchorNode, "table");
        if (inTable) {
            // Move cursor to previous cell.
            this.shiftCursorToTableCell(-1);
            return true;
        }
    }

    insertTable({ rows = 2, cols = 2 } = {}) {
        const tdsHtml = new Array(cols).fill("<td><p><br></p></td>").join("");
        const trsHtml = new Array(rows).fill(`<tr>${tdsHtml}</tr>`).join("");
        const tableHtml = `<table class="table table-bordered o_table"><tbody>${trsHtml}</tbody></table>`;
        let sel = this.shared.getEditableSelection();
        if (!sel.isCollapsed) {
            this.dispatch("DELETE_SELECTION", sel);
        }
        while (!isBlock(sel.anchorNode)) {
            const anchorNode = sel.anchorNode;
            const isTextNode = anchorNode.nodeType === Node.TEXT_NODE;
            const newAnchorNode = isTextNode
                ? this.shared.splitTextNode(anchorNode, sel.anchorOffset, DIRECTIONS.LEFT) + 1 &&
                  anchorNode
                : this.shared.splitElement(anchorNode, sel.anchorOffset).shift();
            const newPosition = rightPos(newAnchorNode);
            sel = this.shared.setSelection(
                { anchorNode: newPosition[0], anchorOffset: newPosition[1] },
                { normalize: false }
            );
        }
        const [table] = this.shared.domInsert(parseHTML(this.document, tableHtml));
        this.dispatch("ADD_STEP");
        this.shared.setCursorStart(table.querySelector("p"));
    }
    addColumn({ position, reference } = {}) {
        const columnIndex = getColumnIndex(reference);
        const table = closestElement(reference, "table");
        const tableWidth = table.style.width ? parseFloat(table.style.width) : table.clientWidth;
        const referenceColumn = table.querySelectorAll(`tr td:nth-of-type(${columnIndex + 1})`);
        const referenceCellWidth = reference.style.width
            ? parseFloat(reference.style.width)
            : reference.clientWidth;
        // Temporarily set widths so proportions are respected.
        const firstRow = table.querySelector("tr");
        const firstRowCells = [...firstRow.children].filter(
            (child) => child.nodeName === "TD" || child.nodeName === "TH"
        );
        let totalWidth = 0;
        for (const cell of firstRowCells) {
            const width = cell.style.width ? parseFloat(cell.style.width) : cell.clientWidth;
            cell.style.width = width + "px";
            // Spread the widths to preserve proportions.
            // -1 for the width of the border of the new column.
            const newWidth = Math.max(
                Math.round((width * tableWidth) / (tableWidth + referenceCellWidth - 1)),
                13
            );
            cell.style.width = newWidth + "px";
            totalWidth += newWidth;
        }
        referenceColumn.forEach((cell, rowIndex) => {
            const newCell = this.document.createElement("td");
            const p = this.document.createElement("p");
            p.append(this.document.createElement("br"));
            newCell.append(p);
            cell[position](newCell);
            if (rowIndex === 0) {
                newCell.style.width = cell.style.width;
                totalWidth += parseFloat(cell.style.width);
            }
        });
        if (totalWidth !== tableWidth - 1) {
            // -1 for the width of the border of the new column.
            firstRowCells[firstRowCells.length - 1].style.width =
                parseFloat(firstRowCells[firstRowCells.length - 1].style.width) +
                (tableWidth - totalWidth - 1) +
                "px";
        }
        // Fix the table and row's width so it doesn't change.
        table.style.width = tableWidth + "px";
    }
    addRow({ position, reference } = {}) {
        const referenceRowHeight = reference.style.height
            ? parseFloat(reference.style.height)
            : reference.clientHeight;
        const newRow = this.document.createElement("tr");
        newRow.style.height = referenceRowHeight + "px";
        const cells = reference.querySelectorAll("td");
        const referenceRowWidths = [...cells].map(
            (cell) => cell.style.width || cell.clientWidth + "px"
        );
        newRow.append(
            ...Array.from(Array(cells.length)).map(() => {
                const td = this.document.createElement("td");
                const p = this.document.createElement("p");
                p.append(this.document.createElement("br"));
                td.append(p);
                return td;
            })
        );
        reference[position](newRow);
        newRow.style.height = referenceRowHeight + "px";
        // Preserve the width of the columns (applied only on the first row).
        if (getRowIndex(newRow) === 0) {
            let columnIndex = 0;
            for (const column of newRow.children) {
                column.style.width = referenceRowWidths[columnIndex];
                cells[columnIndex].style.width = "";
                columnIndex++;
            }
        }
    }
    removeColumn({ cell }) {
        const table = closestElement(cell, "table");
        const cells = [...closestElement(cell, "tr").querySelectorAll("th, td")];
        const index = cells.findIndex((td) => td === cell);
        const siblingCell = cells[index - 1] || cells[index + 1];
        table.querySelectorAll(`tr td:nth-of-type(${index + 1})`).forEach((td) => td.remove());
        // @todo @phoenix should I call dispatch('DELETE_TABLE', table) or this.deleteTable?
        // not sure we should move the cursor?
        siblingCell
            ? this.shared.setCursorStart(siblingCell)
            : this.dispatch("DELETE_TABLE", { table });
    }
    removeRow({ row }) {
        const table = closestElement(row, "table");
        const siblingRow = row.previousElementSibling || row.nextElementSibling;
        row.remove();
        // not sure we should move the cursor?
        siblingRow
            ? this.shared.setCursorStart(siblingRow.querySelector("td"))
            : this.dispatch("DELETE_TABLE", { table });
    }
    moveColumn({ position, cell }) {
        const columnIndex = getColumnIndex(cell);
        const nColumns = cell.parentElement.children.length;
        if (
            columnIndex < 0 ||
            (position === "left" && columnIndex === 0) ||
            (position !== "left" && columnIndex === nColumns - 1)
        ) {
            return;
        }

        const trs = cell.parentElement.parentElement.children;
        const tdsToMove = [...trs].map((tr) => tr.children[columnIndex]);
        const selectionToRestore = this.shared.getEditableSelection();
        if (position === "left") {
            tdsToMove.forEach((td) => td.previousElementSibling.before(td));
        } else {
            tdsToMove.forEach((td) => td.nextElementSibling.after(td));
        }
        this.shared.setSelection(selectionToRestore);
    }
    moveRow({ position, row }) {
        const selectionToRestore = this.shared.getEditableSelection();
        let adjustedRow;
        if (position === "up") {
            row.previousElementSibling?.before(row);
            adjustedRow = row;
        } else {
            row.nextElementSibling?.after(row);
            adjustedRow = row.previousElementSibling;
        }

        // If the moved row becomes the first row, copy the widths of its td
        // elements from the previous first row, as td widths are only applied
        // to the first row.
        if (!adjustedRow.previousElementSibling) {
            adjustedRow.childNodes.forEach((cell, index) => {
                cell.style.width = adjustedRow.nextElementSibling.childNodes[index].style.width;
            });
        }
        this.shared.setSelection(selectionToRestore);
    }
    resetSize({ table }) {
        table.removeAttribute("style");
        const cells = [...table.querySelectorAll("tr, td")];
        cells.forEach((cell) => {
            const cStyle = cell.style;
            if (cell.tagName === "TR") {
                cStyle.height = "";
            } else {
                cStyle.width = "";
            }
        });
    }
    deleteTable({ table }) {
        table = table || findInSelection(this.shared.getEditableSelection(), "table");
        if (!table) {
            return;
        }
        const p = this.document.createElement("p");
        p.appendChild(this.document.createElement("br"));
        table.before(p);
        table.remove();
        this.shared.setCursorStart(p);
    }

    // @todo @phoenix: handle deleteBackward on table cells
    // deleteBackwardBefore({ targetNode, targetOffset }) {
    //     // If the cursor is at the beginning of a row, prevent deletion.
    //     if (targetNode.nodeType === Node.ELEMENT_NODE && isRow(targetNode) && !targetOffset) {
    //         return true;
    //     }
    // }

    /**
     * Removes fully selected rows or columns, clears the content of selected
     * cells otherwise.
     *
     * @param {NodeListOf<HTMLTableCellElement>} selectedTds - Non-empty
     * NodeList of selected table cells.
     */
    deleteTableCells(selectedTds) {
        const rows = [...closestElement(selectedTds[0], "tr").parentElement.children].filter(
            (child) => child.nodeName === "TR"
        );
        const firstRowCells = [...rows[0].children].filter(
            (child) => child.nodeName === "TD" || child.nodeName === "TH"
        );
        const firstCellRowIndex = getRowIndex(selectedTds[0]);
        const firstCellColumnIndex = getColumnIndex(selectedTds[0]);
        const lastCellRowIndex = getRowIndex(selectedTds[selectedTds.length - 1]);
        const lastCellColumnIndex = getColumnIndex(selectedTds[selectedTds.length - 1]);

        const areFullColumnsSelected =
            firstCellRowIndex === 0 && lastCellRowIndex === rows.length - 1;
        const areFullRowsSelected =
            firstCellColumnIndex === 0 && lastCellColumnIndex === firstRowCells.length - 1;

        if (areFullColumnsSelected) {
            for (let index = firstCellColumnIndex; index <= lastCellColumnIndex; index++) {
                this.removeColumn({ cell: firstRowCells[index] });
            }
            return;
        }

        if (areFullRowsSelected) {
            for (let index = firstCellRowIndex; index <= lastCellRowIndex; index++) {
                this.removeRow({ row: rows[index] });
            }
            return;
        }

        for (const td of selectedTds) {
            // @todo @phoenix this replaces paragraphs by inline content. Is this intended?
            td.replaceChildren(this.document.createElement("br"));
        }
        this.shared.setCursorStart(selectedTds[0]);
    }

    /**
     * @param {Object} range - Range-like object.
     * @param {Array} fullySelectedTables - Non-empty array of table elements.
     */
    deleteRangeWithFullySelectedTables(range, fullySelectedTables) {
        let { startContainer, startOffset, endContainer, endOffset } = range;

        // Expand range to fully include tables.
        const firstTable = fullySelectedTables[0];
        if (firstTable.contains(startContainer)) {
            [startContainer, startOffset] = leftPos(firstTable);
        }
        const lastTable = fullySelectedTables.at(-1);
        if (lastTable.contains(endContainer)) {
            [endContainer, endOffset] = rightPos(lastTable);
        }
        range = { startContainer, startOffset, endContainer, endOffset };

        range = this.shared.deleteRange(range);

        // Normalize deep.
        // @todo @phoenix: Use something from the selection plugin (normalize deep?)
        const [anchorNode, anchorOffset] = getDeepestPosition(
            range.startContainer,
            range.startOffset
        );

        this.shared.setSelection({ anchorNode, anchorOffset });
    }

    handleDeleteRange(range) {
        // @todo @phoenix: this does not depend on the range. This should be
        // optimized by keeping in memory the state of selected cells/tables.
        const fullySelectedTables = [...this.editable.querySelectorAll(".o_selected_table")].filter(
            (table) =>
                [...table.querySelectorAll("td")].every(
                    (td) =>
                        closestElement(td, "table") !== table ||
                        td.classList.contains("o_selected_td")
                )
        );
        if (fullySelectedTables.length) {
            this.deleteRangeWithFullySelectedTables(range, fullySelectedTables);
            return true;
        }

        const selectedTds = this.editable.querySelectorAll(".o_selected_td");
        if (selectedTds.length) {
            this.deleteTableCells(selectedTds);
            // this._toggleTableUi();
            return true;
        }

        return false;
    }

    /**
     * Moves the cursor by shiftIndex table cells.
     *
     * @param {Number} shiftIndex - The index to shift the cursor by.
     * @returns {boolean} - True if the cursor was successfully moved, false otherwise.
     */
    shiftCursorToTableCell(shiftIndex) {
        const sel = this.shared.getEditableSelection();
        const currentTd = closestElement(sel.anchorNode, "td");
        const closestTable = closestElement(currentTd, "table");
        if (!currentTd || !closestTable) {
            return false;
        }
        const tds = [...closestTable.querySelectorAll("td")];
        const cursorDestination = tds[tds.findIndex((td) => currentTd === td) + shiftIndex];
        if (!cursorDestination) {
            return false;
        }
        this.shared.setCursorEnd(lastLeaf(cursorDestination));
        return true;
    }

    updateSelectionTable(selection) {
        this.deselectTable();

        const startTd = closestElement(selection.startContainer, "td");
        const endTd = closestElement(selection.endContainer, "td");
        const startTable = ancestors(selection.startContainer, this.editable)
            .filter((node) => node.nodeName === "TABLE")
            .pop();
        const endTable = ancestors(selection.endContainer, this.editable)
            .filter((node) => node.nodeName === "TABLE")
            .pop();

        const traversedNodes = this.shared.getTraversedNodes({ deep: true });
        if (startTd !== endTd && startTable === endTable) {
            if (!isProtected(startTable) && !isProtecting(startTable)) {
                // The selection goes through at least two different cells ->
                // select cells.
                this.selectTableCells(selection);
            }
        } else if (!traversedNodes.every((node) => closestElement(node.parentElement, "table"))) {
            const traversedTables = new Set(
                traversedNodes
                    .map((node) => closestElement(node, "table"))
                    .filter((node) => node && !isProtected(node) && !isProtecting(node))
            );
            for (const table of traversedTables) {
                // Don't apply several nested levels of selection.
                if (!ancestors(table, this.editable).some((node) => traversedTables.has(node))) {
                    table.classList.toggle("o_selected_table", true);
                    for (const td of [...table.querySelectorAll("td")].filter(
                        (td) => closestElement(td, "table") === table
                    )) {
                        td.classList.toggle("o_selected_td", true);
                    }
                }
            }
        }
    }

    selectTableCells(selection) {
        const table = closestElement(selection.commonAncestorContainer, "table");
        table.classList.toggle("o_selected_table", true);
        const columns = [...table.querySelectorAll("td")].filter(
            (td) => closestElement(td, "table") === table
        );
        const startCol =
            [selection.startContainer, ...ancestors(selection.startContainer, this.editable)].find(
                (node) => node.nodeName === "TD" && closestElement(node, "table") === table
            ) || columns[0];
        const endCol =
            [selection.endContainer, ...ancestors(selection.endContainer, this.editable)].find(
                (node) => node.nodeName === "TD" && closestElement(node, "table") === table
            ) || columns[columns.length - 1];
        const [startRow, endRow] = [closestElement(startCol, "tr"), closestElement(endCol, "tr")];
        const [startColIndex, endColIndex] = [getColumnIndex(startCol), getColumnIndex(endCol)];
        const [startRowIndex, endRowIndex] = [getRowIndex(startRow), getRowIndex(endRow)];
        const [minRowIndex, maxRowIndex] = [
            Math.min(startRowIndex, endRowIndex),
            Math.max(startRowIndex, endRowIndex),
        ];
        const [minColIndex, maxColIndex] = [
            Math.min(startColIndex, endColIndex),
            Math.max(startColIndex, endColIndex),
        ];
        // Create an array of arrays of tds (each of which is a row).
        const grid = [...table.querySelectorAll("tr")]
            .filter((tr) => closestElement(tr, "table") === table)
            .map((tr) => [...tr.children].filter((child) => child.nodeName === "TD"));
        for (const tds of grid.filter((_, index) => index >= minRowIndex && index <= maxRowIndex)) {
            for (const td of tds.filter(
                (_, index) => index >= minColIndex && index <= maxColIndex
            )) {
                td.classList.toggle("o_selected_td", true);
            }
        }
    }

    /**
     * Remove any custom table selection from the editor.
     *
     * @returns {boolean} true if a table was deselected
     */
    deselectTable(root = this.editable) {
        let didDeselectTable = false;
        for (const table of root.querySelectorAll(".o_selected_table")) {
            removeClass(table, "o_selected_table");
            for (const td of table.querySelectorAll(".o_selected_td")) {
                removeClass(td, "o_selected_td");
            }
            didDeselectTable = true;
        }
        return didDeselectTable;
    }

    applyTableColor(color, mode) {
        const selectedTds = [...this.editable.querySelectorAll("td.o_selected_td")].filter(
            (node) => node.isContentEditable
        );
        if (selectedTds.length && mode === "backgroundColor") {
            for (const td of selectedTds) {
                this.shared.colorElement(td, color, mode);
            }
        }
    }

    adjustTraversedNodes(traversedNodes) {
        const modifiedTraversedNodes = [];
        const visitedTables = new Set();
        for (const node of traversedNodes) {
            const selectedTable = closestElement(node, ".o_selected_table");
            if (selectedTable) {
                if (visitedTables.has(selectedTable)) {
                    continue;
                }
                visitedTables.add(selectedTable);
                for (const selectedTd of selectedTable.querySelectorAll(".o_selected_td")) {
                    modifiedTraversedNodes.push(selectedTd, ...descendants(selectedTd));
                }
            } else {
                modifiedTraversedNodes.push(node);
            }
        }
        return modifiedTraversedNodes;
    }
}
