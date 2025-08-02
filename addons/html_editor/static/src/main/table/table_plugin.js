import { Plugin } from "@html_editor/plugin";
import { baseContainerGlobalSelector } from "@html_editor/utils/base_container";
import { isBlock } from "@html_editor/utils/blocks";
import {
    fillEmpty,
    fillShrunkPhrasingParent,
    removeClass,
    splitTextNode,
} from "@html_editor/utils/dom";
import {
    getDeepestPosition,
    isProtected,
    isProtecting,
    isEmptyBlock,
    isTextNode,
    nextLeaf,
    previousLeaf,
    isTableCell,
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
import { getColumnIndex, getRowIndex, getTableCells } from "@html_editor/utils/table";
import { isBrowserFirefox } from "@web/core/browser/feature_detection";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";

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
 * @property { TablePlugin['turnIntoHeader'] } turnIntoHeader
 * @property { TablePlugin['moveColumn'] } moveColumn
 * @property { TablePlugin['moveRow'] } moveRow
 * @property { TablePlugin['removeColumn'] } removeColumn
 * @property { TablePlugin['removeRow'] } removeRow
 * @property { TablePlugin['turnIntoRow'] } turnIntoRow
 * @property { TablePlugin['resetRowHeight'] } resetRowHeight
 * @property { TablePlugin['resetColumnWidth'] } resetColumnWidth
 * @property { TablePlugin['resetTableSize'] } resetTableSize
 * @property { TablePlugin['clearColumnContent'] } clearColumnContent
 * @property { TablePlugin['clearRowContent'] } clearRowContent
 */

/**
 * This plugin only contains the table manipulation and selection features. All UI overlay
 * code is located in the table_ui plugin
 */
export class TablePlugin extends Plugin {
    static id = "table";
    static dependencies = [
        "baseContainer",
        "dom",
        "history",
        "selection",
        "delete",
        "split",
        "color",
    ];
    static shared = [
        "insertTable",
        "addColumn",
        "addRow",
        "removeColumn",
        "removeRow",
        "moveColumn",
        "turnIntoHeader",
        "turnIntoRow",
        "moveRow",
        "resetRowHeight",
        "resetColumnWidth",
        "resetTableSize",
        "clearColumnContent",
        "clearRowContent",
    ];
    resources = {
        user_commands: [
            {
                id: "insertTable",
                run: (params) => {
                    this.insertTable(params);
                },
                isAvailable: isHtmlContentSupported,
            },
        ],

        /** Handlers */
        selectionchange_handlers: this.updateSelectionTable.bind(this),
        clipboard_content_processors: this.processContentForClipboard.bind(this),
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
        targeted_nodes_processors: this.adjustTargetedNodes.bind(this),
        move_node_whitelist_selectors: "table",
        collapsed_selection_toolbar_predicate: (selectionData) =>
            !!closestElement(selectionData.editableSelection.anchorNode, ".o_selected_td"),
    };

    setup() {
        this.addDomListener(this.editable, "mousedown", this.onMousedown);
        this.addDomListener(this.editable, "mouseup", this.onMouseup);
        this.addDomListener(this.editable, "keydown", (ev) => {
            this._isKeyDown = true;
            const arrowHandled = ["arrowup", "control+arrowup", "arrowdown", "control+arrowdown"];
            if (arrowHandled.includes(getActiveHotkey(ev))) {
                this.navigateCell(ev);
            }
            const shiftArrowHandled = [
                "shift+arrowup",
                "shift+arrowright",
                "shift+arrowdown",
                "shift+arrowleft",
                "control+shift+arrowup",
                "control+shift+arrowright",
                "control+shift+arrowdown",
                "control+shift+arrowleft",
            ];
            if (shiftArrowHandled.includes(getActiveHotkey(ev))) {
                this.isShiftArrowKeyboardSelection = true;
                this.updateTableKeyboardSelection(ev);
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
        const baseContainer = this.dependencies.baseContainer.createBaseContainer();
        fillShrunkPhrasingParent(baseContainer);
        const baseContainerHtml = baseContainer.outerHTML;
        const tdsHtml = new Array(cols).fill(`<td>${baseContainerHtml}</td>`).join("");
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
        this.dependencies.selection.setCursorStart(
            table.querySelector(baseContainerGlobalSelector)
        );
        this.dependencies.history.addStep();
    }
    /**
     * @param {'before'|'after'} position
     * @param {HTMLTableCellElement} reference
     */
    addColumn(position, reference) {
        const columnIndex = getColumnIndex(reference);
        const table = closestElement(reference, "table");
        const tableWidth = table.style.width && parseFloat(table.style.width);
        const referenceColumn = table.querySelectorAll(
            `tr :is(td, th):nth-of-type(${columnIndex + 1})`
        );
        const referenceCellWidth = reference.style.width
            ? parseFloat(reference.style.width)
            : reference.clientWidth;
        // Temporarily set widths so proportions are respected.
        const firstRow = table.querySelector("tr");
        const firstRowCells = [...firstRow.children].filter(
            (child) => child.nodeName === "TD" || child.nodeName === "TH"
        );
        let totalWidth = 0;
        if (tableWidth) {
            for (const cell of firstRowCells) {
                const width = parseFloat(cell.style.width);
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
        }
        referenceColumn.forEach((cell, rowIndex) => {
            const newCell = this.document.createElement(cell.tagName);
            const baseContainer = this.dependencies.baseContainer.createBaseContainer();
            baseContainer.append(this.document.createElement("br"));
            newCell.append(baseContainer);
            cell[position](newCell);
            // If the first row is a header, ensure the new column's
            // first cell is also marked as a header (<th>).
            if (rowIndex === 0 && cell.classList.contains("o_table_header")) {
                newCell.classList.add("o_table_header");
            }
            if (rowIndex === 0 && tableWidth) {
                newCell.style.width = cell.style.width;
                totalWidth += parseFloat(cell.style.width);
            }
        });
        if (tableWidth) {
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
    }
    /**
     * @param {'before'|'after'} position
     * @param {HTMLTableRowElement} reference
     */
    addRow(position, reference) {
        const referenceRowHeight = reference.style.height && parseFloat(reference.style.height);
        const newRow = this.document.createElement("tr");
        if (referenceRowHeight) {
            newRow.style.height = referenceRowHeight + "px";
        }
        const cells = reference.querySelectorAll("td, th");
        const referenceRowWidths = [...cells].map((cell) => cell.style.width);
        newRow.append(
            ...Array.from(cells).map(() => {
                const td = this.document.createElement("td");
                const baseContainer = this.dependencies.baseContainer.createBaseContainer();
                baseContainer.append(this.document.createElement("br"));
                td.append(baseContainer);
                return td;
            })
        );
        reference[position](newRow);
        if (referenceRowHeight) {
            newRow.style.height = referenceRowHeight + "px";
        }
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
     * @param {HTMLTableRowElement} reference
     */
    turnIntoHeader(reference) {
        const preserveSelection = this.dependencies.selection.preserveSelection();
        [...reference.children].forEach((td) => {
            if (td.nodeName == "TD") {
                const th = this.document.createElement("th");
                if (td.style?.cssText.length) {
                    th.style.cssText = td.style?.cssText;
                }
                th.classList.add("o_table_header");
                th.append(...td.childNodes);
                td.replaceWith(th);
            }
        });
        preserveSelection.restore();
    }
    /**
     * @param {HTMLTableRowElement} reference
     */
    turnIntoRow(reference) {
        const preserveSelection = this.dependencies.selection.preserveSelection();
        [...reference.children].forEach((th) => {
            if (th.nodeName == "TH") {
                const td = this.document.createElement("td");
                if (th.style?.cssText.length) {
                    td.style.cssText = th.style?.cssText;
                }
                td.append(...th.childNodes);
                th.replaceWith(td);
            }
        });
        preserveSelection.restore();
    }
    /**
     * @param {HTMLTableCellElement} cell
     */
    removeColumn(cell) {
        const table = closestElement(cell, "table");
        const cells = [...closestElement(cell, "tr").querySelectorAll("th, td")];
        const index = cells.findIndex((td) => td === cell);
        const siblingCell = cells[index - 1] || cells[index + 1];
        table
            .querySelectorAll(`tr :is(td, th):nth-of-type(${index + 1})`)
            .forEach((td) => td.remove());
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
            ? this.dependencies.selection.setCursorStart(siblingRow.querySelector("td, th"))
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
            const isPreviousRowHeader =
                [...row.previousElementSibling.children][0].nodeName === "TH";
            row.previousElementSibling?.before(row);
            adjustedRow = row;
            if (isPreviousRowHeader) {
                this.turnIntoHeader(row);
                this.turnIntoRow(row.nextElementSibling);
            }
        } else {
            const isRowHeader = [...row.children][0].nodeName === "TH";
            row.nextElementSibling?.after(row);
            adjustedRow = row.previousElementSibling;
            if (isRowHeader) {
                this.turnIntoHeader(adjustedRow);
                this.turnIntoRow(row);
            }
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
    normalizeRowHeight(table) {
        const rows = [...table.rows];
        const referenceRow = rows.find((row) => !row.style.height);
        const referenceRowHeight = parseFloat(getComputedStyle(referenceRow).height);
        rows.forEach((row) => {
            if (
                row.style.height &&
                Math.abs(parseFloat(row.style.height) - referenceRowHeight) <= 1
            ) {
                row.style.height = "";
            }
        });
    }

    /**
     * @param {HTMLTableRowElement} row
     */
    resetRowHeight(row) {
        const table = closestElement(row, "table");
        row.style.height = "";
        this.normalizeRowHeight(table);
    }

    /**
     * @param {HTMLTableElement} table
     */
    normalizeColumnWidth(table) {
        const rows = [...table.rows];
        const firstRowCells = [...rows[0].cells];
        const tableWidth = parseFloat(table.style.width);
        if (tableWidth) {
            const expectedCellWidth = tableWidth / firstRowCells.length;
            firstRowCells.forEach((cell, i) => {
                const cellWidth = parseFloat(cell.style.width);
                if (cellWidth && Math.abs(cellWidth - expectedCellWidth) <= 1) {
                    rows.forEach((row) => (row.cells[i].style.width = ""));
                }
            });
        }
    }

    /**
     * @param {HTMLTableCellElement} cell
     */
    resetColumnWidth(cell) {
        const currentCellWidth = parseFloat(cell.style.width);
        if (!currentCellWidth) {
            return;
        }

        const table = closestElement(cell, "table");
        const tableWidth = parseFloat(table.style.width);
        const currentRow = cell.parentElement;
        const currentRowCells = [...currentRow.cells];
        const rowCellCount = currentRowCells.length;
        const expectedCellWidth = tableWidth / rowCellCount;
        const widthDifference = currentCellWidth - expectedCellWidth;
        const currentColumnIndex = getColumnIndex(cell);

        let totalWidthLeftOfCell = 0,
            totalWidthRightOfCell = 0;
        currentRowCells.forEach((rowCell, i) => {
            const cellWidth = parseFloat(rowCell.style.width) || rowCell.clientWidth;
            if (i < currentColumnIndex) {
                totalWidthLeftOfCell += cellWidth;
            } else if (i > currentColumnIndex) {
                totalWidthRightOfCell += cellWidth;
            }
        });

        let expectedWidthLeftOfCell = currentColumnIndex * expectedCellWidth;
        let expectedWidthRightOfCell = (rowCellCount - 1 - currentColumnIndex) * expectedCellWidth;
        let cellsToAdjust = [];
        for (
            let i = currentColumnIndex - 1;
            i >= 0 && Math.abs(expectedWidthLeftOfCell - totalWidthLeftOfCell) > 1;
            i--
        ) {
            cellsToAdjust.push(currentRowCells[i]);
            totalWidthLeftOfCell -=
                parseFloat(currentRowCells[i].style.width) || currentRowCells[i].clientWidth;
            expectedWidthLeftOfCell -= expectedCellWidth;
        }
        for (
            let j = currentColumnIndex + 1;
            j < rowCellCount && Math.abs(expectedWidthRightOfCell - totalWidthRightOfCell) > 1;
            j++
        ) {
            cellsToAdjust.push(currentRowCells[j]);
            totalWidthRightOfCell -=
                parseFloat(currentRowCells[j].style.width) || currentRowCells[j].clientWidth;
            expectedWidthRightOfCell -= expectedCellWidth;
        }

        cellsToAdjust = cellsToAdjust.filter((adjCell) => {
            const cellWidth = parseFloat(adjCell.style.width) || adjCell.clientWidth;
            return widthDifference > 0
                ? cellWidth < expectedCellWidth
                : cellWidth > expectedCellWidth;
        });

        const totalWidthForAdjustment = cellsToAdjust.reduce((width, adjCell) => {
            const cellWidth = parseFloat(adjCell.style.width) || adjCell.clientWidth;
            return width + Math.abs(expectedCellWidth - cellWidth);
        }, 0);

        cell.style.width = `${expectedCellWidth}px`;
        cellsToAdjust.forEach((adjCell) => {
            const adjCellWidth = parseFloat(adjCell.style.width) || adjCell.clientWidth;
            const adjustmentWidth =
                (Math.abs(expectedCellWidth - adjCellWidth) / totalWidthForAdjustment) *
                Math.abs(widthDifference);
            adjCell.style.width = `${
                adjCellWidth + (widthDifference > 0 ? adjustmentWidth : -adjustmentWidth)
            }px`;
        });
        this.normalizeColumnWidth(table);
    }

    /**
     * @param {HTMLTableElement} table
     */
    resetTableSize(table) {
        table.removeAttribute("style");
        const cells = [...table.querySelectorAll("tr, td, th")];
        cells.forEach((cell) => {
            const cStyle = cell.style;
            if (cell.tagName === "TR") {
                cStyle.height = "";
            } else {
                cStyle.width = "";
            }
        });
    }
    /**
     * @param {HTMLTableCellElement} cell
     */
    clearColumnContent(cell) {
        const table = closestElement(cell, "table");
        const cells = [...closestElement(cell, "tr").querySelectorAll("th, td")];
        const index = cells.findIndex((td) => td === cell);
        table.querySelectorAll(`tr :is(td, th):nth-of-type(${index + 1})`).forEach((td) => {
            const baseContainer = this.dependencies.baseContainer.createBaseContainer();
            fillEmpty(baseContainer);
            td.replaceChildren(baseContainer);
        });
    }
    /**
     * @param {HTMLTableRowElement} row
     */
    clearRowContent(row) {
        row.querySelectorAll("td, th").forEach((td) => {
            const baseContainer = this.dependencies.baseContainer.createBaseContainer();
            fillEmpty(baseContainer);
            td.replaceChildren(baseContainer);
        });
    }
    deleteTable(table) {
        table =
            table || findInSelection(this.dependencies.selection.getEditableSelection(), "table");
        if (!table) {
            return;
        }
        const baseContainer = this.dependencies.baseContainer.createBaseContainer();
        baseContainer.appendChild(this.document.createElement("br"));
        table.before(baseContainer);
        table.remove();
        this.dependencies.selection.setCursorStart(baseContainer);
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
            const baseContainer = this.dependencies.baseContainer.createBaseContainer();
            baseContainer.appendChild(this.document.createElement("br"));
            td.replaceChildren(baseContainer);
        }
        this.dependencies.selection.setCursorStart(selectedTds[0].firstChild);
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
                [...table.querySelectorAll("td, th")].every(
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
        const currentTd = closestElement(sel.anchorNode, isTableCell);
        const closestTable = closestElement(currentTd, "table");
        if (!currentTd || !closestTable) {
            return false;
        }
        const tds = [...closestTable.querySelectorAll("td, th")];
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
                closestElement(ev.target, isTableCell) !==
                    closestElement(selection.focusNode, isTableCell)
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

    /**
     * Sets selection in table to make cell selection
     * rectangularly when pressing shift + arrow key.
     *
     * @private
     * @param {KeyboardEvent} ev
     */
    updateTableKeyboardSelection(ev) {
        const selection = this.dependencies.selection.getSelectionData().deepEditableSelection;
        const startTable = closestElement(selection.anchorNode, "table");
        const endTable = closestElement(selection.focusNode, "table");
        if (!(startTable || endTable)) {
            return;
        }
        const [startTd, endTd] = [
            closestElement(selection.anchorNode, isTableCell),
            closestElement(selection.focusNode, isTableCell),
        ];
        if (startTable !== endTable) {
            // Deselect the table if it was fully selected.
            if (endTable) {
                const deselectingBackward =
                    ["ArrowLeft", "ArrowUp"].includes(ev.key) &&
                    selection.direction === DIRECTIONS.RIGHT;
                const deselectingForward =
                    ["ArrowRight", "ArrowDown"].includes(ev.key) &&
                    selection.direction === DIRECTIONS.LEFT;
                let targetNode;
                if (deselectingBackward) {
                    targetNode = endTable.previousElementSibling;
                } else if (deselectingForward) {
                    targetNode = endTable.nextElementSibling;
                }
                if (targetNode) {
                    ev.preventDefault();
                    this.dependencies.selection.setSelection({
                        anchorNode: selection.anchorNode,
                        anchorOffset: selection.anchorOffset,
                        focusNode: targetNode,
                        focusOffset: deselectingBackward ? nodeSize(targetNode) : 0,
                    });
                }
            }
            return;
        }
        // Handle selection for the single cell.
        if (startTd === endTd && !startTd.classList.contains("o_selected_td")) {
            const { focusNode, focusOffset } = selection;
            // Do not prevent default when there is a text in cell.
            if (focusNode.nodeType === Node.TEXT_NODE) {
                const textNodes = descendants(startTd).filter(isTextNode);
                const lastTextChild = textNodes.pop();
                const firstTextChild = textNodes.shift();
                const isAtTextBoundary = {
                    ArrowRight: nodeSize(focusNode) === focusOffset && focusNode === lastTextChild,
                    ArrowLeft: focusOffset === 0 && focusNode === firstTextChild,
                    ArrowUp: focusNode === firstTextChild,
                    ArrowDown: focusNode === lastTextChild,
                };
                if (isAtTextBoundary[ev.key]) {
                    ev.preventDefault();
                    this.selectTableCells(this.dependencies.selection.getEditableSelection());
                }
            } else {
                ev.preventDefault();
                this.selectTableCells(this.dependencies.selection.getEditableSelection());
            }
            return;
        }
        // Select cells symmetrically.
        const endCellPosition = { x: getRowIndex(endTd), y: getColumnIndex(endTd) };
        const tds = [...startTable.rows].map((row) => [...row.cells]);
        let targetTd, targetNode;
        switch (ev.key) {
            case "ArrowUp": {
                if (endCellPosition.x > 0) {
                    targetTd = tds[endCellPosition.x - 1][endCellPosition.y];
                } else {
                    targetNode = previousLeaf(startTable, this.editable);
                }
                break;
            }
            case "ArrowDown": {
                if (endCellPosition.x < tds.length - 1) {
                    targetTd = tds[endCellPosition.x + 1][endCellPosition.y];
                } else {
                    targetNode = nextLeaf(startTable, this.editable);
                }
                break;
            }
            case "ArrowRight": {
                if (endCellPosition.y < tds[0].length - 1) {
                    targetTd = tds[endCellPosition.x][endCellPosition.y + 1];
                }
                break;
            }
            case "ArrowLeft": {
                if (endCellPosition.y > 0) {
                    targetTd = tds[endCellPosition.x][endCellPosition.y - 1];
                }
                break;
            }
        }
        if (targetTd || targetNode) {
            this.dependencies.selection.setSelection({
                anchorNode: selection.anchorNode,
                anchorOffset: selection.anchorOffset,
                focusNode: targetTd || targetNode,
                focusOffset: 0,
            });
        }
        ev.preventDefault();
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
        if (!selectionData.documentSelectionIsInEditable) {
            return;
        }
        const selection = selectionData.editableSelection;
        const startTd = closestElement(selection.startContainer, isTableCell);
        const endTd = closestElement(selection.endContainer, isTableCell);
        const selectSingleCell =
            startTd &&
            startTd === endTd &&
            startTd.classList.contains("o_selected_td") &&
            this.isShiftArrowKeyboardSelection;
        if (!(startTd && startTd === endTd) || this._isKeyDown) {
            delete this._isKeyDown;
            // Prevent deselecting single cell unless selection changes
            // through keyboard.
            this.deselectTable();
        }
        delete this.isShiftArrowKeyboardSelection;
        const startTable = ancestors(selection.startContainer, this.editable)
            .filter((node) => node.nodeName === "TABLE")
            .pop();
        const endTable = ancestors(selection.endContainer, this.editable)
            .filter((node) => node.nodeName === "TABLE")
            .pop();

        const targetedNodes = this.dependencies.selection.getTargetedNodes();
        if ((startTd !== endTd || selectSingleCell) && startTable === endTable) {
            if (!isProtected(startTable) && !isProtecting(startTable)) {
                // The selection goes through at least two different cells ->
                // select cells.
                // Select single cell if selection goes from two cells to
                // one using shift + arrow key.
                this.selectTableCells(selection);
            }
        } else if (!targetedNodes.every((node) => closestElement(node.parentElement, "table"))) {
            const endSelectionTable = closestElement(selection.focusNode, "table");
            const endSelectionTableTds = endSelectionTable && getTableCells(endSelectionTable);
            const targetedTds = new Set(
                targetedNodes.map((node) => closestElement(node, isTableCell))
            );
            const isTableFullySelected = endSelectionTableTds?.every((td) => targetedTds.has(td));
            if (endSelectionTable && !isTableFullySelected) {
                // Make sure all the cells are targeted in actual selection
                // when selecting full table. If not, they will be selected
                // forcefully and updateSelectionTable will be called again.
                const targetTd =
                    selection.direction === DIRECTIONS.RIGHT
                        ? endSelectionTableTds.pop()
                        : endSelectionTableTds.shift();
                this.dependencies.selection.setSelection({
                    anchorNode: selection.anchorNode,
                    anchorOffset: selection.anchorOffset,
                    focusNode: targetTd,
                    focusOffset: selection.direction === DIRECTIONS.RIGHT ? nodeSize(targetTd) : 0,
                });
            }
            const targetedTables = new Set(
                targetedNodes
                    .map((node) => closestElement(node, "table"))
                    .filter((node) => node && !isProtected(node) && !isProtecting(node))
            );
            for (const table of targetedTables) {
                // Don't apply several nested levels of selection.
                if (!ancestors(table, this.editable).some((node) => targetedTables.has(node))) {
                    table.classList.toggle("o_selected_table", true);
                    for (const td of getTableCells(table)) {
                        td.classList.toggle("o_selected_td", true);
                        this.dispatchTo("deselect_custom_selected_nodes_handlers", td);
                    }
                }
            }
        }
    }

    onMousedown(ev) {
        this._currentMouseState = ev.type;
        this._lastMousedownPosition = [ev.x, ev.y];
        this.deselectTable();
        const isPointerInsideCell = this.isPointerInsideCell(ev);
        const td = closestElement(ev.target, isTableCell);
        if (
            isPointerInsideCell &&
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
        if (isPointerInsideCell && ev.detail === 1) {
            this.editable.addEventListener("mousemove", this.onMousemove);
            const currentSelection = this.dependencies.selection.getEditableSelection();
            // disable dragging on table
            this.dependencies.selection.setCursorStart(currentSelection.anchorNode);
        }
    }

    onMouseup(ev) {
        delete this._mouseMovePositionWhenAllContentsSelected;
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
        const td = closestElement(ev.target, isTableCell);
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
        const startTd = closestElement(selection.startContainer, isTableCell);
        const endTd = closestElement(selection.endContainer, isTableCell);
        if (startTd && startTd === endTd && !isProtected(startTd) && !isProtecting(startTd)) {
            const targetedNodes = this.dependencies.selection.getTargetedNodes();
            const cellContents = descendants(startTd);
            /** @todo Test. Should probably use areNodeContentsFullySelected. */
            const areCellContentsFullySelected = cellContents
                .filter((d) => !isBlock(d))
                .every((child) => targetedNodes.includes(child));
            if (areCellContentsFullySelected) {
                const SENSITIVITY = 5;
                if (!this._mouseMovePositionWhenAllContentsSelected) {
                    this._mouseMovePositionWhenAllContentsSelected = [ev.clientX, ev.clientY];
                }
                const isMovingAwayFromSelection =
                    Math.abs(ev.clientX - this._mouseMovePositionWhenAllContentsSelected[0]) >=
                    SENSITIVITY;
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
        const currentCell = closestElement(anchorNode, isTableCell);
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
        if (!table) {
            return;
        }
        table.classList.toggle("o_selected_table", true);
        const columns = getTableCells(table);
        const startCol =
            [selection.startContainer, ...ancestors(selection.startContainer, this.editable)].find(
                (node) => isTableCell(node) && closestElement(node, "table") === table
            ) || columns[0];
        const endCol =
            [selection.endContainer, ...ancestors(selection.endContainer, this.editable)].find(
                (node) => isTableCell(node) && closestElement(node, "table") === table
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
            .map((tr) => [...tr.children].filter(isTableCell));
        for (const tds of grid.filter((_, index) => index >= minRowIndex && index <= maxRowIndex)) {
            for (const td of tds.filter(
                (_, index) => index >= minColIndex && index <= maxColIndex
            )) {
                td.classList.toggle("o_selected_td", true);
                this.dispatchTo("deselect_custom_selected_nodes_handlers", td);
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
        const selectedTds = [...this.editable.querySelectorAll(".o_selected_td")].filter(
            (node) => node.isContentEditable
        );
        if (selectedTds.length && mode === "backgroundColor") {
            if (previewMode) {
                // Temporarily remove backgroundColor applied by "o_selected_td" class with !important.
                selectedTds.forEach((td) => td.classList.remove("o_selected_td"));
            }
            for (const td of selectedTds) {
                this.dependencies.color.colorElement(td, color, mode);
                if (color) {
                    td.style["color"] = getComputedStyle(td).color;
                } else {
                    td.style["color"] = "";
                }
            }
        }
    }

    adjustTargetedNodes(targetedNodes) {
        const modifiedTargetedNodes = [];
        const visitedTables = new Set();
        for (const node of targetedNodes) {
            const selectedTable = closestElement(node, ".o_selected_table");
            if (selectedTable) {
                if (visitedTables.has(selectedTable)) {
                    continue;
                }
                visitedTables.add(selectedTable);
                for (const selectedTd of selectedTable.querySelectorAll(".o_selected_td")) {
                    modifiedTargetedNodes.push(selectedTd, ...descendants(selectedTd));
                }
            } else {
                modifiedTargetedNodes.push(node);
            }
        }
        return modifiedTargetedNodes;
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

    /**
     * @param {DocumentFragment} clonedContents
     * @param {import("@html_editor/core/selection_plugin").EditorSelection} selection
     */
    processContentForClipboard(clonedContents, selection) {
        if (clonedContents.firstChild.nodeName === "TR" || isTableCell(clonedContents.firstChild)) {
            // We enter this case only if selection is within single table.
            const table = closestElement(selection.commonAncestorContainer, "table");
            const tableClone = table.cloneNode(true);
            // A table is considered fully selected if it is nested inside a
            // cell that is itself selected, or if all its own cells are
            // selected.
            const isTableFullySelected =
                (table.parentElement && !!closestElement(table.parentElement, ".o_selected_td")) ||
                getTableCells(table).every((td) => td.classList.contains("o_selected_td"));
            if (!isTableFullySelected) {
                for (const td of tableClone.querySelectorAll(":is(td, th):not(.o_selected_td)")) {
                    if (closestElement(td, "table") === tableClone) {
                        // ignore nested
                        td.remove();
                    }
                }
                const trsWithoutTd = Array.from(tableClone.querySelectorAll("tr")).filter(
                    (row) => !row.querySelector("td, th")
                );
                for (const tr of trsWithoutTd) {
                    if (closestElement(tr, "table") === tableClone) {
                        // ignore nested
                        tr.remove();
                    }
                }
            }
            // If it is fully selected, clone the whole table rather than
            // just its rows.
            clonedContents = tableClone;
        }
        const startTable = closestElement(selection.startContainer, "table");
        if (clonedContents.firstChild.nodeName === "TABLE" && startTable) {
            // Make sure the full leading table is copied.
            clonedContents.firstChild.after(startTable.cloneNode(true));
            clonedContents.firstChild.remove();
        }
        const endTable = closestElement(selection.endContainer, "table");
        if (clonedContents.lastChild.nodeName === "TABLE" && endTable) {
            // Make sure the full trailing table is copied.
            clonedContents.lastChild.before(endTable.cloneNode(true));
            clonedContents.lastChild.remove();
        }
        this.deselectTable(clonedContents);
        return clonedContents;
    }
}
