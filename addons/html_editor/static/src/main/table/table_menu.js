import { closestElement } from "@html_editor/utils/dom_traversal";
import { Component, onMounted, onWillUnmount, useExternalListener, useRef } from "@odoo/owl";
import { getRowIndex, getSelectedCellsMergeInfo } from "@html_editor/utils/table";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { isEmpty, isTableCell } from "@html_editor/utils/dom_info";
import { getBaseContainerSelector } from "@html_editor/utils/base_container";

export class TableMenu extends Component {
    static template = "html_editor.TableMenu";
    static props = {
        type: String, // column or row
        moveColumn: Function,
        addColumn: Function,
        removeColumn: Function,
        moveRow: Function,
        addRow: Function,
        removeRow: Function,
        turnIntoHeader: Function,
        turnIntoRow: Function,
        resetRowHeight: Function,
        resetColumnWidth: Function,
        resetTableSize: Function,
        clearColumnContent: Function,
        mergeSelectedCells: Function,
        unmergeSelectedCell: Function,
        clearRowContent: Function,
        toggleAlternatingRows: Function,
        buildTableGrid: Function,
        overlay: Object,
        tableDragDropOverlay: Object,
        dropdownState: Object,
        target: { validate: (el) => el.nodeType === Node.ELEMENT_NODE },
        document: { validate: (p) => p.nodeType === Node.DOCUMENT_NODE },
        editable: { validate: (p) => p.nodeType === Node.ELEMENT_NODE },
        direction: { type: String, optional: true },
    };
    static defaultProps = { direction: "ltr" };
    static components = { Dropdown, DropdownItem };

    setup() {
        if (this.props.type === "column") {
            this.isFirst = this.props.target.cellIndex === 0;
            this.isLast = !this.props.target.nextElementSibling;
        } else {
            const tr = this.props.target.parentElement;
            this.isFirst = !tr.previousElementSibling;
            this.isLast = !tr.nextElementSibling;
            this.isTableHeader = [...tr.children][0].nodeName === "TH";
        }
        this.editableDocument = this.props.editable.ownerDocument;
        this.tableGrid = this.props.buildTableGrid(closestElement(this.props.target, "table"));
        this.items = this.props.type === "column" ? this.colItems() : this.rowItems();
        this.menuRef = useRef("menuRef");
        const onPointerDown = (ev) => this.onPointerDown(ev);
        onMounted(() => {
            this.menuRef?.el.addEventListener("pointerdown", onPointerDown);
        });
        onWillUnmount(() => {
            this.menuRef?.el.removeEventListener("pointerdown", onPointerDown);
        });
        useExternalListener(this.props.document, "pointerup", this.onPointerUp);
        if (this.props.document !== document) {
            // Listen outside the iframe.
            useExternalListener(document, "pointerup", this.onPointerUp);
        }
    }

    get hasCustomTableSize() {
        const table = closestElement(this.props.target, "table");
        if (!table) {
            return false;
        }
        const rows = [...table.rows];
        const rowHasHeight = rows.some((row) => row.style.height);
        const colgroup = table.querySelector("colgroup");
        return rowHasHeight || colgroup;
    }

    get hasCustomRowHeight() {
        return !!closestElement(this.props.target, "tr").style.height;
    }

    get hasCustomColumnWidth() {
        const table = closestElement(this.props.target, "table");
        const index = this.tableGrid[0].indexOf(closestElement(this.props.target, isTableCell));
        const colgroup = table.querySelector("colgroup");
        if (colgroup) {
            return colgroup.children[index].style.width;
        }
        return false;
    }

    get hasContent() {
        const baseContainerSelector = getBaseContainerSelector();
        const cell = this.props.target;
        const colIndex = this.tableGrid[0].indexOf(cell);
        const targetCells =
            this.props.type === "row"
                ? [...cell.parentElement.children]
                : this.tableGrid.map((row) => row[colIndex]);
        return targetCells.some((td) => {
            const { children } = td;
            return !(
                children.length === 1 &&
                children[0].matches(baseContainerSelector) &&
                isEmpty(children[0])
            );
        });
    }

    onSelected(item) {
        item.action(this.props.target);
        this.props.overlay.close();
    }

    onPointerDown(ev) {
        const target = this.props.target;
        let hasMergedSpan = false;
        if (this.props.type === "column") {
            const colIndex = this.tableGrid[0].indexOf(target);
            hasMergedSpan = this.tableGrid.some((row) => row[colIndex].colSpan > 1);
        } else {
            const colIndex = getRowIndex(target);
            hasMergedSpan = this.tableGrid[colIndex].some((cell) => cell.rowSpan > 1);
        }
        // Do not allow drag-and-drop on merged cells
        if (hasMergedSpan) {
            return;
        }
        this.longPressTimer = setTimeout(() => {
            this.props.overlay.close();
            // Open the TableDragDrop overlay.
            this.props.tableDragDropOverlay.open({
                target: target,
                props: {
                    type: this.props.type,
                    pointerPos: { x: ev.clientX, y: ev.clientY },
                    target: target,
                    document: this.props.document,
                    editable: this.props.editable,
                    close: () => this.props.tableDragDropOverlay.close(),
                    moveRow: this.props.moveRow,
                    moveColumn: this.props.moveColumn,
                    tableGrid: this.tableGrid,
                },
            });
        }, 200); // long press threshold
    }

    onPointerUp() {
        // Cancel long-press to prevent tableDragDropOverlay.
        clearTimeout(this.longPressTimer);
        delete this.longPressTimer;
    }

    isCurrentOrAdjacentCellRowSpanned(position) {
        const td = this.props.target;
        const tr = closestElement(td, "tr");
        const rowIndex = getRowIndex(tr);
        const adjacentRowIndex = position === "move_down" ? rowIndex + 1 : rowIndex - 1;
        return (
            this.tableGrid[rowIndex]?.some((cell) => cell?.rowSpan > 1) ||
            this.tableGrid[adjacentRowIndex]?.some((cell) => cell?.rowSpan > 1)
        );
    }

    isCurrentOrAdjacentCellColSpanned(position) {
        const targetCell = this.props.target;
        const columnIndex = this.tableGrid[0].indexOf(targetCell);
        const adjacentIndex = position === "move_right" ? columnIndex + 1 : columnIndex - 1;
        return this.tableGrid.some(
            (row) => row[columnIndex]?.colSpan > 1 || row[adjacentIndex]?.colSpan > 1
        );
    }

    colItems() {
        const ltr = this.props.direction === "ltr";
        const { canMerge, canUnmerge, cells, spanType } = getSelectedCellsMergeInfo(
            this.editableDocument,
            this.tableGrid,
            this.props.target
        );
        return [
            !this.isFirst && {
                name: "move_left",
                icon: "fa-chevron-left disabled",
                text: ltr ? _t("Move left") : _t("Move right"),
                action: (target) =>
                    this.props.moveColumn(this.tableGrid[0].indexOf(target) - 1, target),
                disable: this.isCurrentOrAdjacentCellColSpanned("move_left"),
                tooltip: _t("Merged columns cannot be moved left or right."),
            },
            !this.isLast && {
                name: "move_right",
                icon: "fa-chevron-right",
                text: ltr ? _t("Move right") : _t("Move left"),
                action: (target) =>
                    this.props.moveColumn(this.tableGrid[0].indexOf(target) + 1, target),
                disable: this.isCurrentOrAdjacentCellColSpanned("move_right"),
                tooltip: _t("Merged columns cannot be moved left or right."),
            },
            {
                name: "insert_left",
                icon: "fa-plus",
                text: ltr ? _t("Insert left") : _t("Insert right"),
                action: this.props.addColumn.bind(this, "before"),
            },
            {
                name: "insert_right",
                icon: "fa-plus",
                text: ltr ? _t("Insert right") : _t("Insert left"),
                action: this.props.addColumn.bind(this, "after"),
            },
            {
                name: "delete",
                icon: "fa-trash",
                text: _t("Delete"),
                action: this.props.removeColumn.bind(this),
            },
            this.hasCustomColumnWidth && {
                name: "reset_column_size",
                icon: "fa-table",
                text: _t("Reset column size"),
                action: (target) =>
                    this.props.resetColumnWidth(closestElement(target, isTableCell)),
            },
            this.hasCustomTableSize && {
                name: "reset_table_size",
                icon: "fa-table",
                text: _t("Reset table size"),
                action: (target) => this.props.resetTableSize(closestElement(target, "table")),
            },
            this.hasContent && {
                name: "clear_content",
                icon: "fa-times-circle",
                text: _t("Clear content"),
                action: this.props.clearColumnContent.bind(this),
            },
            cells.length > 1 && {
                name: "merge_cell",
                icon: "fa fa-compress",
                text: _t("Merge Cells"),
                disable: !canMerge,
                tooltip: _t("Only rows or cells selection can be merged"),
                action: () => this.props.mergeSelectedCells(cells, spanType),
            },
            canUnmerge && {
                name: "unmerge_cell",
                icon: "fa fa-compress",
                text: _t("Unmerge Cells"),
                action: this.props.unmergeSelectedCell.bind(this),
            },
        ].filter(Boolean);
    }

    rowItems() {
        const table = closestElement(this.props.target, "table");
        const hasAlternatingRowClass = table.classList.contains("o_alternating_rows");
        const { canMerge, canUnmerge, cells, spanType } = getSelectedCellsMergeInfo(
            this.editableDocument,
            this.tableGrid,
            this.props.target
        );
        return [
            this.isFirst &&
                !this.isTableHeader && {
                    name: "make_header",
                    icon: "fa-th-large",
                    text: _t("Turn into header"),
                    action: (target) => this.props.turnIntoHeader(target.parentElement),
                },
            this.isFirst &&
                this.isTableHeader && {
                    name: "remove_header",
                    icon: "fa-table",
                    text: _t("Turn into row"),
                    action: (target) => this.props.turnIntoRow(target.parentElement),
                },
            !this.isFirst && {
                name: "move_up",
                icon: "fa-chevron-up",
                text: _t("Move up"),
                action: (target) =>
                    this.props.moveRow(getRowIndex(target) - 1, target.parentElement),
                disable: this.isCurrentOrAdjacentCellRowSpanned("move_up"),
                tooltip: _t("Merged rows cannot be moved up or down."),
            },
            !this.isLast && {
                name: "move_down",
                icon: "fa-chevron-down",
                text: _t("Move down"),
                action: (target) =>
                    this.props.moveRow(getRowIndex(target) + 1, target.parentElement),
                disable: this.isCurrentOrAdjacentCellRowSpanned("move_down"),
                tooltip: _t("Merged rows cannot be moved up or down."),
            },
            !this.isTableHeader && {
                name: "insert_above",
                icon: "fa-plus",
                text: _t("Insert above"),
                action: (target) => this.props.addRow("before", target.parentElement),
            },
            {
                name: "insert_below",
                icon: "fa-plus",
                text: _t("Insert below"),
                action: (target) => this.props.addRow("after", target.parentElement),
            },
            {
                name: "toggle_alternating_rows",
                icon: "fa-paint-brush",
                text: hasAlternatingRowClass
                    ? _t("Clear alternate colors")
                    : _t("Alternate row colors"),
                action: () => this.props.toggleAlternatingRows(table),
            },
            {
                name: "delete",
                icon: "fa-trash",
                text: _t("Delete"),
                action: (target) => this.props.removeRow(target.parentElement),
            },
            this.hasCustomRowHeight && {
                name: "reset_row_size",
                icon: "fa-table",
                text: _t("Reset row size"),
                action: (target) => this.props.resetRowHeight(closestElement(target, "tr")),
            },
            this.hasCustomTableSize && {
                name: "reset_table_size",
                icon: "fa-table",
                text: _t("Reset table size"),
                action: (target) => this.props.resetTableSize(closestElement(target, "table")),
            },
            this.hasContent && {
                name: "clear_content",
                icon: "fa-times-circle",
                text: _t("Clear content"),
                action: (target) => this.props.clearRowContent(target.parentElement),
            },
            cells.length > 1 && {
                name: "merge_cell",
                icon: "fa fa-compress",
                text: _t("Merge Cells"),
                disable: !canMerge,
                tooltip: _t("Only rows or cells selection can be merged"),
                action: () => this.props.mergeSelectedCells(cells, spanType),
            },
            canUnmerge && {
                name: "unmerge_cell",
                icon: "fa fa-compress",
                text: _t("Unmerge Cells"),
                action: this.props.unmergeSelectedCell.bind(this),
            },
        ].filter(Boolean);
    }
}
