import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { Component, reactive } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { visitNode } from "../utils";

/**
 * @typedef {Object} CellInfo
 * @property {number} length
 * @property {number} cellIndex
 */

class TableMenu extends Component {
    static template = "html_editor.TableMenu";
    static props = {
        type: String, // column or row
        overlay: Object,
        dropdownState: Object,
        target: { validate: (el) => el.nodeType === Node.ELEMENT_NODE },
        editable: { validate: (el) => el.nodeType === Node.ELEMENT_NODE },
        addColumn: Function,
        removeColumn: Function,
    };
    static components = { Dropdown, DropdownItem };

    setup() {
        this.items = this.props.type === "column" ? this.colItems() : [];
    }

    colItems() {
        return [
            {
                name: "insert_left",
                icon: "fa-plus",
                text: _t("Insert left"),
                action: this.insertColumn.bind(this, "before"),
            },
            {
                name: "insert_right",
                icon: "fa-plus",
                text: _t("Insert right"),
                action: this.insertColumn.bind(this, "after"),
            },
            {
                name: "delete",
                icon: "fa-trash",
                text: _t("Delete"),
                action: this.deleteColumn.bind(this),
            },
        ];
    }

    insertColumn(position, target) {
        this.props.addColumn({ position, reference: target });
        this.props.editable.focus();
    }

    deleteColumn(target) {
        this.props.removeColumn({ cell: target });
        this.props.editable.focus();
    }
    onSelected(item) {
        item.action(this.props.target);
        this.props.overlay.close();
    }
}

function setColspan(cell, colspan) {
    if (colspan < 1) {
        return;
    }
    if (colspan === 1) {
        cell.removeAttribute("colspan");
    } else {
        cell.setAttribute("colspan", `${colspan}`);
    }
}

function setStyleProperty(element, name, value) {
    const style = element.style;
    if (value === undefined) {
        style.removeProperty(name);
        if (!style.length) {
            element.removeAttribute("style");
        }
    } else {
        style.setProperty(name, value);
    }
}

function* getAllConditionalBlocks(el) {
    const previousBlocks = [...iterConditionalSiblings(el, true)];
    for (let index = previousBlocks.length - 1; index >= 0; index--) {
        const _el = previousBlocks[index];
        if (_el !== el) {
            yield _el;
        }
    }
    yield* iterConditionalSiblings(el);
}

function* iterConditionalSiblings(el, reverse = false) {
    const condition = ["t-if", "t-elif", "t-else"].find((attr) => el.hasAttribute(attr));
    if (!condition) {
        return;
    }
    const next = reverse ? "previousElementSibling" : "nextElementSibling";
    let includeTif = reverse ? true : condition === "t-if";
    while (el) {
        if (el.hasAttribute("t-if")) {
            if (includeTif && reverse) {
                yield el;
                return;
            }
            if (!includeTif) {
                return;
            }
            if (includeTif) {
                yield el;
                includeTif = false;
            }
        } else {
            yield el;
        }
        const sibl = el[next];
        el =
            sibl && ["t-if", "t-elif", "t-else"].some((attr) => sibl.hasAttribute(attr))
                ? sibl
                : null;
    }
}

const CELL_TAGS = ["Q-TH", "Q-TD"];
const CSS_COL_COUNT_PROP = "--q-table-col-count";
const CSS_COL_SIZE_PROP = "--q-cell-col-size";
export class QWebTablePlugin extends Plugin {
    static id = "qweb_table_plugin";
    static dependencies = ["baseContainer", "overlay", "selection", "history"];
    resources = {
        clean_for_save_handlers: ({ root }) => this.clean(root),
        normalize_handlers: this.normalize.bind(this),
    };

    setup() {
        for (const table of this.editable.querySelectorAll("q-table")) {
            visitNode(table, (node) => {
                if (node.tagName !== "T") {
                    node.classList.add("oe_unbreakable");
                }
                return !CELL_TAGS.includes(node.tagName);
            });
        }
        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.colMenu = this.dependencies.overlay.createOverlay(
            TableMenu,
            {
                positionOptions: {
                    position: "top-fit",
                    offsetY: 0,
                },
            },
            { sequence: 30 }
        );

        this.isMenuOpened = false;
        const closeMenus = () => {
            if (this.isMenuOpened) {
                this.isMenuOpened = false;
                this.colMenu.close();
            }
        };
        this.addDomListener(this.document, "scroll", closeMenus, true);
        this.addDomListener(this.document, "pointermove", this.onMouseMove);
    }

    onMouseMove(ev) {
        const target = ev.target;
        if (this.isMenuOpened) {
            return;
        }
        if (
            CELL_TAGS.includes(target.tagName) &&
            target !== this.activeTd &&
            this.editable.contains(target)
        ) {
            if (ev.target.isContentEditable) {
                this.setActiveTd(target);
            }
        } else if (this.activeTd) {
            const isOverlay = target.closest(".o-overlay-container");
            if (isOverlay) {
                return;
            }
            const parentTd = closestElement(target, (el) => CELL_TAGS.includes(el.tagName));
            if (!parentTd) {
                this.setActiveTd(null);
            }
        }
    }

    setActiveTd(td) {
        this.activeTd = td;
        this.colMenu.close();
        if (!td) {
            return;
        }
        const table = closestElement(td, "q-table");
        if (table.querySelector("q-tr").contains(td)) {
            this.colMenu.open({
                target: td,
                props: {
                    editable: this.editable,
                    type: "column",
                    overlay: this.colMenu,
                    target: td,
                    dropdownState: this.createDropdownState(),
                    addColumn: this.addColumn.bind(this),
                    removeColumn: this.removeColumn.bind(this),
                },
            });
        }
    }

    createDropdownState(menuToClose) {
        const dropdownState = reactive({
            isOpen: false,
            open: () => {
                dropdownState.isOpen = true;
                menuToClose?.close();
                this.isMenuOpened = true;
            },
            close: () => {
                dropdownState.isOpen = false;
                this.isMenuOpened = false;
            },
        });
        return dropdownState;
    }

    addColumn(payload) {
        const insertedCells = this._addColumn(payload);
        this.dependencies.selection.setCursorStart(insertedCells[0]);
        this.dependencies.history.addStep();
    }

    _addColumn({ position, reference }) {
        const table = closestElement(reference, "q-table");

        const { cells } = new TableSizeComputer().compute(table);
        const { cellIndex, length } = cells.get(reference);
        const insertedCells = [];
        const done = new Set();
        for (const cellEl of cells.keys()) {
            let target = cellEl;
            for (const condition of iterConditionalSiblings(target, position === "before")) {
                target = condition;
            }
            if (done.has(target)) {
                continue;
            }
            done.add(target);
            const cellInfo = cells.get(target);
            if (cellInfo.cellIndex === cellIndex && cellInfo.length === length) {
                const newTd = this.createElementFrom(cellEl);
                target.insertAdjacentElement(
                    position === "before" ? "beforebegin" : "afterend",
                    newTd
                );
                insertedCells.push(newTd);
                continue;
            }
            if (TableSizeComputer.areOverlappingCellInfo(cellInfo, { cellIndex, length })) {
                const colspan = parseInt(target.getAttribute("colspan") || "1") + 1;
                setColspan(target, colspan);
                continue;
            }
        }
        this._normalize(table);
        return insertedCells;
    }

    clean(element) {
        const cleanTableNode = (node) => {
            if (node.tagName === "Q-TABLE") {
                setStyleProperty(node, CSS_COL_COUNT_PROP, undefined);
            }
            const isCell = CELL_TAGS.includes(node.tagName);
            if (isCell) {
                setStyleProperty(node, CSS_COL_SIZE_PROP, undefined);
            }
            node.classList.remove("oe_unbreakable");
            if (node.classList.length === 0) {
                node.removeAttribute("class");
            }
            return !isCell;
        };

        for (const table of element.querySelectorAll("q-table")) {
            visitNode(table, cleanTableNode);
        }
    }

    removeColumn(payload) {
        const table = closestElement(payload.cell, "q-table");
        this._removeColumn(payload);
        const firstCell = table.querySelector(CELL_TAGS.join(","));
        this.dependencies.selection.setCursorEnd(firstCell);
        this.dependencies.history.addStep();
    }

    _removeColumn({ cell }) {
        const table = closestElement(cell, "q-table");

        const { cells } = new TableSizeComputer().compute(table);
        const { cellIndex, length } = cells.get(cell);
        const removedCells = [];
        const done = new Set();
        for (const cellEl of cells.keys()) {
            if (done.has(cellEl)) {
                continue;
            }
            const cellInfo = cells.get(cellEl);

            if (cellIndex === cellInfo.cellIndex && length === cellInfo.length) {
                for (const removed of this._removeCell(cellEl)) {
                    removedCells.push(removed);
                    done.add(removed);
                }
                continue;
            }
            if (TableSizeComputer.areOverlappingCellInfo(cellInfo, { length, cellIndex })) {
                const colspan = parseInt(cellEl.getAttribute("colspan") || "1") - 1;
                if (colspan === 0) {
                    for (const removed of this._removeCell(cellEl)) {
                        removedCells.push(removed);
                        done.add(removed);
                    }
                    continue;
                }
                setColspan(cellEl, colspan);
            }
        }
        this._normalize(table);
        return removedCells;
    }

    _removeCell(cellEl) {
        const toRemove = [...getAllConditionalBlocks(cellEl)];
        if (!toRemove.length) {
            toRemove.push(cellEl);
        }
        for (const _el of toRemove) {
            _el.remove();
        }
        return toRemove;
    }

    createElementFrom(fromElement) {
        const tagName = fromElement.tagName.toLowerCase();
        const newElement = this.document.createElement(tagName);
        const baseContainer = this.dependencies.baseContainer.createBaseContainer("DIV");
        baseContainer.append(this.document.createElement("br"));
        newElement.append(baseContainer);
        newElement.classList.add("oe_unbreakable");
        return newElement;
    }

    normalize(el) {
        for (const table of el.querySelectorAll("q-table")) {
            this._normalize(table);
        }
    }
    _normalize(table) {
        const { cells, baseLineRow } = new TableSizeComputer().compute(table);

        setStyleProperty(table, CSS_COL_COUNT_PROP, `${baseLineRow.length}`);
        for (const [cellEl, info] of cells.entries()) {
            setStyleProperty(
                cellEl,
                CSS_COL_SIZE_PROP,
                info.length === 1 ? undefined : `${info.length}`
            );
        }
    }
}

/**
 * Recursively traverses a table-like tree in order to compute each cell's start position and length (colspan)
 * It stops traversing when encountering a table cell (q-th, q-td)
 * It handles qweb conditions (t-if/t-elif/t-else).
 * The algo goes:
 * - start traversing the table depth first.
 * - when encountering a row (q-tr), reset cellIndex and cellCount to 0
 * - when encountering a cell (q-td, q-th), increment cellIndex and cellCount
 * - don't traverse the cell itself
 * - a cell can have a colspan, increment cellIndex accordingly
 * - when encoutering a t-if: stop temporarly the depth first traversal
 * - store counters
 * - count cells in each mutually exclusive branch
 * - set counters to the maximum yield among the branches
 * - resume normal traversal.
 */
class TableSizeComputer {
    /**
     * @param {CellInfo} info1
     * @param {CellInfo} info2
     */
    static areOverlappingCellInfo(info1, info2) {
        if (info1.cellIndex <= info2.cellIndex) {
            return info1.cellIndex + info1.length > info2.cellIndex;
        }
        if (info1.cellIndex > info2.cellIndex) {
            return info2.cellIndex + info2.length > info1.cellIndex;
        }
    }

    compute(table) {
        this.cells = new Map();
        this.rows = new Map();
        this.rowIndex = 0;
        this.cellIndex = 0;
        this.cellCount = 0;
        this.maxCellLength = 0;
        this.processChildren(table);
        return {
            rows: this.rows,
            cells: this.cells,
            maxCellLength: this.maxCellLength,
            baseLineRow: this.baseLineRow,
        };
    }

    processCell(cell, params) {
        const cellLength = parseInt(cell.getAttribute("colspan") || "1");
        const cellIndex = this.cellIndex;
        this.cellCount++;
        this.cellIndex = this.cellIndex + cellLength;
        this.cells.set(cell, { length: cellLength, cellEl: cell, rowEl: params.rowEl, cellIndex });
    }

    processRow(el, params) {
        const row = { rowIndex: this.rowIndex++ };
        this.rows.set(el, row);
        let next = el.firstElementChild;
        while (next) {
            const _next = this.processElement(next, { ...params, rowEl: el });
            next = _next === undefined ? next.nextElementSibling : _next;
        }
        if (!this.baseLineRow) {
            this.baseLineRow = row;
        }
        row.length = this.cellIndex;
        row.cellCount = this.cellCount;
        this.maxCellLength = Math.max(this.cellIndex, this.maxCellLength);
        this.cellIndex = 0;
        this.cellCount = 0;
    }

    processConditions(el, params) {
        // we are about to compute the index of elements inside a t-if/t-elif/t-else
        // sequence of direct siblings.
        // These siblings are mutually exclusive. Hence, we store the current index,
        // go inside the branch, then reset the index to its value.
        // The resulting end index of these siblings in the maximum of them all.
        const cellIndex = this.cellIndex;
        let maxCellIndex = cellIndex;

        const cellCount = this.cellCount;
        let maxCellCount = cellCount;

        let next;
        for (const conditional of iterConditionalSiblings(el)) {
            this.processElement(conditional, params, false);
            maxCellIndex = Math.max(maxCellIndex, this.cellIndex);
            maxCellCount = Math.max(maxCellCount, this.cellCount);
            this.cellIndex = cellIndex;
            this.cellCount = cellCount;
            next = conditional;
        }
        this.cellIndex = maxCellIndex;
        this.cellCount = maxCellCount;
        return next && next.nextElementSibling;
    }

    processChildren(el, params = {}) {
        let next = el.firstElementChild;
        while (next) {
            const _next = this.processElement(next, params);
            next = _next === undefined ? next.nextElementSibling : _next;
        }
    }

    processElement(el, params = {}, processConditions = true) {
        if (el.hasAttribute("t-set")) {
            return;
        }

        if (processConditions) {
            const directive = ["t-if", "t-elif", "t-else"].find((attr) => el.hasAttribute(attr));
            if (directive === "t-if") {
                return this.processConditions(el, params);
            } else if (directive && el.tagName === "T") {
                // Don't plunge into t-elif/t-else: this has been done already
                return;
            }
        }
        if (CELL_TAGS.includes(el.tagName)) {
            return this.processCell(el, params);
        }
        if (el.tagName === "Q-TR") {
            return this.processRow(el, params);
        }
        return this.processChildren(el, params);
    }
}
