import { Plugin } from "@html_editor/plugin";
import { isBlock } from "@html_editor/utils/blocks";
import { removeClass, splitTextNode } from "@html_editor/utils/dom";
import {
    getDeepestPosition,
    isProtected,
    isProtecting,
    isEmptyBlock,
} from "@html_editor/utils/dom_info";
import {
    ancestors,
    closestElement,
    createDOMPathGenerator,
    descendants,
    firstLeaf,
    lastLeaf,
} from "@html_editor/utils/dom_traversal";
import { parseHTML } from "@html_editor/utils/html";
import { DIRECTIONS, leftPos, rightPos, nodeSize } from "@html_editor/utils/position";
import { withSequence } from "@html_editor/utils/resource";
import { findInSelection } from "@html_editor/utils/selection";
import { getColumnIndex, getRowIndex } from "@html_editor/utils/table";
import { isBrowserFirefox } from "@web/core/browser/feature_detection";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";

export const BORDER_SENSITIVITY = 5;

const tableInnerComponents = new Set(["THEAD", "TBODY", "TFOOT", "TR", "TH", "TD"]);
function isUnremovableTableComponent(node, root) {
    if (!tableInnerComponents.has(node.nodeName)) {
        return false;
    }
    if (!root) {
        return true;
    }
    const closestTable = closestElement(node, "table");
    return !root.contains(closestTable);
}

/**
 * @typedef { Object } TableShared
 * @property { TablePlugin['addColumn'] } addColumn
 * @property { TablePlugin['addRow'] } addRow
 * @property { TablePlugin['moveColumn'] } moveColumn
 * @property { TablePlugin['moveRow'] } moveRow
 * @property { TablePlugin['removeColumn'] } removeColumn
 * @property { TablePlugin['removeRow'] } removeRow
 * @property { TablePlugin['resetTableSize'] } resetTableSize
 */

/**
 * This plugin only contains the table manipulation and selection features. All UI overlay
 * code is located in the table_ui plugin
 */
export class TablePlugin extends Plugin {
    static id = "table";
    static dependencies = ["dom", "history", "selection", "delete", "split", "color"];
    static shared = [
        "insertTable",
        "addColumn",
        "addRow",
        "removeColumn",
        "removeRow",
        "moveColumn",
        "moveRow",
        "resetTableSize",
    ];
    resources = {
        user_commands: [
            {
                id: "insertTable",
                run: (params) => {
                    this.insertTable(params);
                },
            },
        ],

        /** Handlers */
        selectionchange_handlers: this.updateSelectionTable.bind(this),
        clean_handlers: this.deselectTable.bind(this),
        clean_for_save_handlers: ({ root }) => this.deselectTable(root),
        before_line_break_handlers: this.resetTableSelection.bind(this),
        before_split_block_handlers: this.resetTableSelection.bind(this),

        /** Overrides */
        tab_overrides: withSequence(20, this.handleTab.bind(this)),
        shift_tab_overrides: withSequence(20, this.handleShiftTab.bind(this)),
        delete_range_overrides: this.handleDeleteRange.bind(this),
        color_apply_overrides: this.applyTableColor.bind(this),

        unremovable_node_predicates: isUnremovableTableComponent,
        unsplittable_node_predicates: (node) =>
            node.nodeName === "TABLE" || tableInnerComponents.has(node.nodeName),
        fully_selected_node_predicates: (node) => !!closestElement(node, ".o_selected_td"),
        traversed_nodes_processors: this.adjustTraversedNodes.bind(this),
    };

    setup() {
        this.addDomListener(this.editable, "mousedown", this.onMousedown);
        this.addDomListener(this.editable, "mouseup", this.onMouseup);
        this.addDomListener(this.editable, "keydown", (ev) => {
            const handled = ["arrowup", "control+arrowup", "arrowdown", "control+arrowdown"];
            if (handled.includes(getActiveHotkey(ev))) {
                this.navigateCell(ev);
            }
        });
        this.onMousemove = this.onMousemove.bind(this);
    }

    handleTab() {
        const selection = this.dependencies.selection.getEditableSelection();
        const inTable = closestElement(selection.anchorNode, "table");
        if (inTable) {
            // Move cursor to next cell.
            const shouldAddNewRow = !this.shiftCursorToTableCell(1);
            if (shouldAddNewRow) {
                this.addRow("after", findInSelection(selection, "tr"));
                this.shiftCursorToTableCell(1);
                this.dependencies.history.addStep();
            }
            return true;
        }
    }

    handleShiftTab() {
        const selection = this.dependencies.selection.getEditableSelection();
        const inTable = closestElement(selection.anchorNode, "table");
        if (inTable) {
            // Move cursor to previous cell.
            this.shiftCursorToTableCell(-1);
            return true;
        }
    }

    createTable({ rows = 2, cols = 2 } = {}) {
        const tdsHtml = new Array(cols).fill("<td><p><br></p></td>").join("");
        const trsHtml = new Array(rows).fill(`<tr>${tdsHtml}</tr>`).join("");
        const tableHtml = `<table class="table table-bordered o_table"><tbody>${trsHtml}</tbody></table>`;
        return parseHTML(this.document, tableHtml);
    }

    _insertTable({ rows = 2, cols = 2 } = {}) {
        const newTable = this.createTable({ rows, cols });
        let sel = this.dependencies.selection.getEditableSelection();
        if (!sel.isCollapsed) {
            this.dependencies.delete.deleteSelection();
        }
        while (!isBlock(sel.anchorNode)) {
            const anchorNode = sel.anchorNode;
            const isTextNode = anchorNode.nodeType === Node.TEXT_NODE;
            const newAnchorNode = isTextNode
                ? splitTextNode(anchorNode, sel.anchorOffset, DIRECTIONS.LEFT) + 1 && anchorNode
                : this.dependencies.split.splitElement(anchorNode, sel.anchorOffset).shift();
            const newPosition = rightPos(newAnchorNode);
            sel = this.dependencies.selection.setSelection(
                { anchorNode: newPosition[0], anchorOffset: newPosition[1] },
                { normalize: false }
            );
        }
        const [table] = this.dependencies.dom.insert(newTable);
        return table;
    }
    insertTable({ rows = 2, cols = 2 } = {}) {
        const table = this._insertTable({ rows, cols });
        this.dependencies.selection.setCursorStart(table.querySelector("p"));
        this.dependencies.history.addStep();
    }
    /**
     * @param {'before'|'after'} position
     * @param {HTMLTableCellElement} reference
     */
    addColumn(position, reference) {
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
    /**
     * @param {'before'|'after'} position
     * @param {HTMLTableRowElement} reference
     */
    addRow(position, reference) {
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
    /**
     * @param {HTMLTableCellElement} cell
     */
    removeColumn(cell) {
        const table = closestElement(cell, "table");
        const cells = [...closestElement(cell, "tr").querySelectorAll("th, td")];
        const index = cells.findIndex((td) => td === cell);
        const siblingCell = cells[index - 1] || cells[index + 1];
        table.querySelectorAll(`tr td:nth-of-type(${index + 1})`).forEach((td) => td.remove());
        // not sure we should move the cursor?
        siblingCell
            ? this.dependencies.selection.setCursorStart(siblingCell)
            : this.deleteTable(table);
    }
    /**
     * @param {HTMLTableRowElement} row
     */
    removeRow(row) {
        const table = closestElement(row, "table");
        const siblingRow = row.previousElementSibling || row.nextElementSibling;
        row.remove();
        // not sure we should move the cursor?
        siblingRow
            ? this.dependencies.selection.setCursorStart(siblingRow.querySelector("td"))
            : this.deleteTable(table);
    }
    /**
     * @param {'left'|'right'} position
     * @param {HTMLTableCellElement} cell
     */
    moveColumn(position, cell) {
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
        const selectionToRestore = this.dependencies.selection.getEditableSelection();
        if (position === "left") {
            tdsToMove.forEach((td) => td.previousElementSibling.before(td));
        } else {
            tdsToMove.forEach((td) => td.nextElementSibling.after(td));
        }
        this.dependencies.selection.setSelection(selectionToRestore);
    }
    /**
     * @param {'up'|'down'} position
     * @param {HTMLTableRowElement} row
     */
    moveRow(position, row) {
        const selectionToRestore = this.dependencies.selection.getEditableSelection();
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
        this.dependencies.selection.setSelection(selectionToRestore);
    }
    /**
     * @param {HTMLTableElement} table
     */
    resetTableSize(table) {
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
    deleteTable(table) {
        table =
            table || findInSelection(this.dependencies.selection.getEditableSelection(), "table");
        if (!table) {
            return;
        }
        const p = this.document.createElement("p");
        p.appendChild(this.document.createElement("br"));
        table.before(p);
        table.remove();
        this.dependencies.selection.setCursorStart(p);
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
                this.removeColumn(firstRowCells[index]);
            }
            return;
        }

        if (areFullRowsSelected) {
            for (let index = firstCellRowIndex; index <= lastCellRowIndex; index++) {
                this.removeRow(rows[index]);
            }
            return;
        }

        for (const td of selectedTds) {
            // @todo @phoenix this replaces paragraphs by inline content. Is this intended?
            td.replaceChildren(this.document.createElement("br"));
        }
        this.dependencies.selection.setCursorStart(selectedTds[0]);
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

        range = this.dependencies.delete.deleteRange(range);

        // Normalize deep.
        // @todo @phoenix: Use something from the selection plugin (normalize deep?)
        const [anchorNode, anchorOffset] = getDeepestPosition(
            range.startContainer,
            range.startOffset
        );

        this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
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
        const sel = this.dependencies.selection.getEditableSelection();
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
        this.dependencies.selection.setCursorEnd(lastLeaf(cursorDestination));
        return true;
    }

    hanldeFirefoxSelection(ev = null) {
        const selection = this.document.getSelection();
        if (isBrowserFirefox()) {
            if (!this.dependencies.selection.isSelectionInEditable(selection)) {
                return false;
            }
            if (selection.rangeCount > 1 || selection.anchorNode?.tagName === "TR") {
                // In Firefox, selecting multiple cells within a table using the mouse can create multiple ranges.
                // This behavior can cause the original selection (where the selection started) to be lost.
                // To solve the issue we merge the ranges of the selection together the first time we find
                // selection.rangeCount > 1. Morover, when hitting a double click on a cell, it spans a row
                // inside selection which needs to be simplified here.
                const [anchorNode, anchorOffset] = getDeepestPosition(
                    selection.getRangeAt(0).startContainer,
                    selection.getRangeAt(0).startOffset
                );
                const [focusNode, focusOffset] = getDeepestPosition(
                    selection.getRangeAt(selection.rangeCount - 1).startContainer,
                    selection.getRangeAt(selection.rangeCount - 1).startOffset
                );
                this.dependencies.selection.setSelection({
                    anchorNode,
                    anchorOffset,
                    focusNode,
                    focusOffset,
                });
                return true;
            } else if (
                ev &&
                closestElement(ev.target, "table") ===
                    closestElement(selection.anchorNode, "table") &&
                closestElement(ev.target, "td") !== closestElement(selection.focusNode, "td")
            ) {
                // After the manual update firefox will not be able the table selection automatically
                // so we need to update the selection manually too.
                // When we hover on a new table cell we mark it as the new focusNode.
                this.dependencies.selection.setSelection({
                    anchorNode: selection.anchorNode,
                    anchorOffset: selection.anchorOffset,
                    focusNode: ev.target,
                    focusOffset: 0,
                });
                return true;
            }
        }
        return false;
    }

    updateSelectionTable(selectionData) {
        if (
            this.hanldeFirefoxSelection() ||
            this._isFirefoxDoubleMousedown ||
            this._isTripleClickInTable
        ) {
            // It will be retriggered with selectionchange
            delete this._isFirefoxDoubleMousedown;
            delete this._isTripleClickInTable;
            return;
        }
        this.deselectTable();
        const selection = selectionData.editableSelection;
        const startTd = closestElement(selection.startContainer, "td");
        const endTd = closestElement(selection.endContainer, "td");
        const startTable = ancestors(selection.startContainer, this.editable)
            .filter((node) => node.nodeName === "TABLE")
            .pop();
        const endTable = ancestors(selection.endContainer, this.editable)
            .filter((node) => node.nodeName === "TABLE")
            .pop();

        const traversedNodes = this.dependencies.selection.getTraversedNodes({ deep: true });
        if (startTd !== endTd && startTable === endTable) {
            if (!isProtected(startTable) && !isProtecting(startTable)) {
                // The selection goes through at least two different cells ->
                // select cells. If selection changes after selecting single
                // cell, let it be selected.
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

    onMousedown(ev) {
        this._currentMouseState = ev.type;
        this._lastMousedownPosition = [ev.x, ev.y];
        this.deselectTable();
        const td = closestElement(ev.target, "td");
        if (
            td &&
            !isProtected(td) &&
            !isProtecting(td) &&
            ((isEmptyBlock(td) && ev.detail === 2) || ev.detail === 3)
        ) {
            this.hanldeFirefoxSelection();
            this.selectTableCells(this.dependencies.selection.getEditableSelection());
            if (isBrowserFirefox()) {
                // In firefox, selection changes when hitting mouseclick
                // second time in an empty cell. It calls updateSelectionTable
                // which deselects the single cell. Hence, we need a label
                // to keep it selected.
                this._isFirefoxDoubleMousedown = true;
            }
            if (ev.detail === 3) {
                // Doing a tripleclick on a text will change the selection.
                // In such case updateSelectionTable should not do anything.
                this._isTripleClickInTable = true;
            }
        }
        if (this.isPointerInsideCell(ev)) {
            this.editable.addEventListener("mousemove", this.onMousemove);
            const currentSelection = this.dependencies.selection.getEditableSelection();
            // disable dragging on table
            this.dependencies.selection.setCursorStart(currentSelection.anchorNode);
        }
    }

    onMouseup(ev) {
        this._currentMouseState = ev.type;
        this.editable.removeEventListener("mousemove", this.onMousemove);
    }

    /**
     * Checks if mouse is effectively inside the cell and not overlapping
     * the cell borders to prevent cell selection while resizing table.
     *
     * @param {MouseEvent} ev
     * @returns {Boolean}
     */
    isPointerInsideCell(ev) {
        const td = closestElement(ev.target, "td");
        if (td) {
            const targetRect = td.getBoundingClientRect();
            if (
                ev.clientX > targetRect.x + BORDER_SENSITIVITY &&
                ev.clientX < targetRect.x + td.clientWidth - BORDER_SENSITIVITY &&
                ev.clientY > targetRect.y + BORDER_SENSITIVITY &&
                ev.clientY < targetRect.y + td.clientHeight - BORDER_SENSITIVITY
            ) {
                return true;
            }
        }
        return false;
    }

    onMousemove(ev) {
        if (this._currentMouseState !== "mousedown") {
            return;
        }
        if (this.hanldeFirefoxSelection(ev)) {
            return;
        }
        const selection = this.dependencies.selection.getEditableSelection();
        const docSelection = this.document.getSelection();
        const range = docSelection.rangeCount && docSelection.getRangeAt(0);
        const startTd = closestElement(selection.startContainer, "td");
        const endTd = closestElement(selection.endContainer, "td");
        if (startTd && startTd === endTd && !isProtected(startTd) && !isProtecting(startTd)) {
            const selectedNodes = this.dependencies.selection.getSelectedNodes();
            const cellContents = descendants(startTd);
            const areCellContentsFullySelected = cellContents
                .filter((d) => !isBlock(d))
                .every((child) => selectedNodes.includes(child));
            if (areCellContentsFullySelected) {
                const SENSITIVITY = 5;
                const rangeRect = range.getBoundingClientRect();
                const isMovingAwayFromSelection =
                    ev.clientX > rangeRect.x + rangeRect.width + SENSITIVITY || // moving right
                    ev.clientX < rangeRect.x - SENSITIVITY; // moving left
                if (isMovingAwayFromSelection) {
                    // A cell is fully selected and the mouse is moving away
                    // from the selection, within said cell -> select the cell.
                    this.selectTableCells(selection);
                }
            } else if (
                cellContents.filter(isBlock).every(isEmptyBlock) &&
                Math.abs(
                    ev.clientX -
                        (this._lastMousedownPosition ? this._lastMousedownPosition[0] : ev.clientX)
                ) >= 20
            ) {
                // Handle selecting an empty cell.
                this.selectTableCells(selection);
            }
        }
    }

    navigateCell(ev) {
        const selection = this.dependencies.selection.getSelectionData().deepEditableSelection;
        const anchorNode = selection.anchorNode;
        const currentCell = closestElement(anchorNode, "td");
        const currentTable = closestElement(anchorNode, "table");
        if (!selection.isCollapsed || !currentCell) {
            return;
        }
        const isArrowUp = ev.key === "ArrowUp";
        const cellPosition = {
            row: getRowIndex(currentCell),
            col: getColumnIndex(currentCell),
        };
        const tableRows = [...currentTable.rows].map((row) => [...row.cells]);
        const shouldNavigateCell = (currentNode) => {
            const siblingDirection = isArrowUp ? "previousElementSibling" : "nextElementSibling";
            const direction = isArrowUp ? DIRECTIONS.LEFT : DIRECTIONS.RIGHT;
            const domPath = createDOMPathGenerator(direction, {
                stopTraverseFunction: (node) => node === currentCell,
                stopFunction: (node) => node === currentCell,
            });
            const domPathNode = domPath(currentNode);
            let node = domPathNode.next().value;
            while (node) {
                if ((isBlock(node) && node[siblingDirection]) || node.nodeName === "BR") {
                    return false;
                }
                node = domPathNode.next().value;
            }
            return true;
        };
        const rowOffset = isArrowUp ? -1 : 1;
        let targetNode = tableRows[cellPosition.row + rowOffset]?.[cellPosition.col];
        const siblingElement = isArrowUp
            ? currentTable.previousElementSibling
            : currentTable.nextElementSibling;
        if (!targetNode && siblingElement) {
            // If no target cell is available, navigate to sibling element
            targetNode = siblingElement;
        }
        if (shouldNavigateCell(anchorNode)) {
            ev.preventDefault();
            if (targetNode) {
                targetNode = isArrowUp ? lastLeaf(targetNode) : firstLeaf(targetNode);
                const targetOffset = isArrowUp ? nodeSize(targetNode) : 0;
                this.dependencies.selection.setSelection({
                    anchorNode: targetNode,
                    anchorOffset: targetOffset,
                });
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

    applyTableColor(color, mode, previewMode) {
        const selectedTds = [...this.editable.querySelectorAll("td.o_selected_td")].filter(
            (node) => node.isContentEditable
        );
        if (selectedTds.length && mode === "backgroundColor") {
            if (previewMode) {
                // Temporarily remove backgroundColor applied by "o_selected_td" class with !important.
                selectedTds.forEach((td) => td.classList.remove("o_selected_td"));
            }
            for (const td of selectedTds) {
                this.dependencies.color.colorElement(td, color, mode);
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

    resetTableSelection() {
        const selection = this.dependencies.selection.getEditableSelection({ deep: true });
        const anchorTD = closestElement(selection.anchorNode, ".o_selected_td");
        if (!anchorTD) {
            return;
        }
        this.deselectTable();
        this.dependencies.selection.setSelection({
            anchorNode: anchorTD.firstChild,
            anchorOffset: 0,
            focusNode: anchorTD.lastChild,
            focusOffset: nodeSize(anchorTD.lastChild),
        });
    }
}
