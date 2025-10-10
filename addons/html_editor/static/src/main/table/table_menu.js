import { closestElement } from "@html_editor/utils/dom_traversal";
import { getRowIndex, getSelectedCellsMergeInfo } from "@html_editor/utils/table";
import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";

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
        buildTableGrid: Function,
        overlay: Object,
        dropdownState: Object,
        target: { validate: (el) => el.nodeType === Node.ELEMENT_NODE },
        editable: { validate: (el) => el.nodeType === Node.ELEMENT_NODE },
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
    }

    get hasCustomTableSize() {
        const table = closestElement(this.props.target, "table");
        if (!table) {
            return false;
        }
        const rows = [...table.rows];
        const firstRowCells = [...rows[0].cells];
        const rowHasHeight = rows.some((row) => row.style.height);
        const cellHasWidth = firstRowCells.some((cell) => cell.style.width);
        return rowHasHeight || cellHasWidth;
    }

    get hasCustomRowHeight() {
        return !!this.props.target.closest("tr").style.height;
    }

    get hasCustomColumnWidth() {
        return (
            !!this.props.target.closest("td")?.style?.width ||
            !!this.props.target.closest("th")?.style?.width
        );
    }

    get areAlreadyMerged() {
        const selectedTds = Array.from(this.editableDocument.querySelectorAll(".o_selected_td"));
        const { anchorNode, focusNode, isCollapsed } = this.editableDocument.getSelection();
        if (isCollapsed && anchorNode && closestElement(anchorNode, "td")) {
            selectedTds.push(closestElement(anchorNode, "td"));
        }
        if (
            !selectedTds.length ||
            closestElement(anchorNode, "table") !== closestElement(focusNode, "table")
        ) {
            return false;
        }
        return selectedTds.some((td) => td.colSpan > 1 || td.rowSpan > 1);
    }

    onSelected(item) {
        item.action(this.props.target);
        this.props.overlay.close();
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
        const { canMerge, cells, direction } = getSelectedCellsMergeInfo(
            this.editableDocument,
            this.tableGrid
        );
        return [
            !this.isFirst && {
                name: "move_left",
                icon: "fa-chevron-left disabled",
                text: ltr ? _t("Move left") : _t("Move right"),
                action: this.props.moveColumn.bind(this, "left"),
                disable: this.isCurrentOrAdjacentCellColSpanned("move_left"),
                tooltip: _t("Cannot move merge column left or right"),
            },
            !this.isLast && {
                name: "move_right",
                icon: "fa-chevron-right",
                text: ltr ? _t("Move right") : _t("Move left"),
                action: this.props.moveColumn.bind(this, "right"),
                disable: this.isCurrentOrAdjacentCellColSpanned("move_right"),
                tooltip: _t("Cannot move merge column left or right"),
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
                action: (target) => this.props.resetColumnWidth(target.closest("td, th")),
            },
            this.hasCustomTableSize && {
                name: "reset_table_size",
                icon: "fa-table",
                text: _t("Reset table size"),
                action: (target) => this.props.resetTableSize(target.closest("table")),
            },
            {
                name: "clear_content",
                icon: "fa-times-circle",
                text: _t("Clear content"),
                action: this.props.clearColumnContent.bind(this),
            },
            direction !== "colSpan" && {
                name: "merge_cell",
                icon: "fa fa-compress",
                text: _t("Merge Cells"),
                disable: !canMerge,
                tooltip: _t("only rows or cells selection can be merged"),
                action: () => this.props.mergeSelectedCells(cells, direction),
            },
            this.areAlreadyMerged && {
                name: "unmerge_cell",
                icon: "fa fa-compress",
                text: _t("Unmerge Cells"),
                action: this.props.unmergeSelectedCell.bind(this),
            },
        ].filter(Boolean);
    }

    rowItems() {
        const { canMerge, cells, direction } = getSelectedCellsMergeInfo(
            this.editableDocument,
            this.tableGrid
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
                action: (target) => this.props.moveRow("up", target.parentElement),
                disable: this.isCurrentOrAdjacentCellRowSpanned("move_up"),
                tooltip: _t("Cannot move merge row up or down"),
            },
            !this.isLast && {
                name: "move_down",
                icon: "fa-chevron-down",
                text: _t("Move down"),
                action: (target) => this.props.moveRow("down", target.parentElement),
                disable: this.isCurrentOrAdjacentCellRowSpanned("move_down"),
                tooltip: _t("Cannot move merge row up or down"),
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
                name: "delete",
                icon: "fa-trash",
                text: _t("Delete"),
                action: (target) => this.props.removeRow(target.parentElement),
            },
            this.hasCustomRowHeight && {
                name: "reset_row_size",
                icon: "fa-table",
                text: _t("Reset row size"),
                action: (target) => this.props.resetRowHeight(target.closest("tr")),
            },
            this.hasCustomTableSize && {
                name: "reset_table_size",
                icon: "fa-table",
                text: _t("Reset table size"),
                action: (target) => this.props.resetTableSize(target.closest("table")),
            },
            {
                name: "clear_content",
                icon: "fa-times-circle",
                text: _t("Clear content"),
                action: (target) => this.props.clearRowContent(target.parentElement),
            },
            direction !== "rowSpan" && {
                name: "merge_cell",
                icon: "fa fa-compress",
                text: _t("Merge Cells"),
                disable: !canMerge,
                tooltip: _t("only rows or cells selection can be merged"),
                action: () => this.props.mergeSelectedCells(cells, direction),
            },
            this.areAlreadyMerged && {
                name: "unmerge_cell",
                icon: "fa fa-compress",
                text: _t("Unmerge Cells"),
                action: this.props.unmergeSelectedCell.bind(this),
            },
        ].filter(Boolean);
    }
}
