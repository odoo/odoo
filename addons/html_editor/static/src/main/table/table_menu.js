import { closestElement } from "@html_editor/utils/dom_traversal";
import { Component, onMounted, onWillUnmount, useExternalListener, useRef } from "@odoo/owl";
import { getColumnIndex, getRowIndex } from "@html_editor/utils/table";
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
        clearRowContent: Function,
        toggleAlternatingRows: Function,
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

    onSelected(item) {
        item.action(this.props.target);
        this.props.overlay.close();
    }

    onPointerDown(ev) {
        this.longPressTimer = setTimeout(() => {
            this.props.overlay.close();
            // Open the TableDragDrop overlay.
            this.props.tableDragDropOverlay.open({
                target: this.props.target,
                props: {
                    type: this.props.type,
                    pointerPos: { x: ev.clientX, y: ev.clientY },
                    target: this.props.target,
                    document: this.props.document,
                    editable: this.props.editable,
                    close: () => this.props.tableDragDropOverlay.close(),
                    moveRow: this.props.moveRow,
                    moveColumn: this.props.moveColumn,
                },
            });
        }, 200); // long press threshold
    }

    onPointerUp() {
        // Cancel long-press to prevent tableDragDropOverlay.
        clearTimeout(this.longPressTimer);
        delete this.longPressTimer;
    }

    colItems() {
        const ltr = this.props.direction === "ltr";
        return [
            !this.isFirst && {
                name: "move_left",
                icon: "fa-chevron-left disabled",
                text: ltr ? _t("Move left") : _t("Move right"),
                action: (target) => this.props.moveColumn(getColumnIndex(target) - 1, target),
            },
            !this.isLast && {
                name: "move_right",
                icon: "fa-chevron-right",
                text: ltr ? _t("Move right") : _t("Move left"),
                action: (target) => this.props.moveColumn(getColumnIndex(target) + 1, target),
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
        ].filter(Boolean);
    }

    rowItems() {
        const table = closestElement(this.props.target, "table");
        const hasAlternatingRowClass = table.classList.contains("o_alternating_rows");
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
                    this.props.moveRow(getRowIndex(target.parentElement) - 1, target.parentElement),
            },
            !this.isLast && {
                name: "move_down",
                icon: "fa-chevron-down",
                text: _t("Move down"),
                action: (target) =>
                    this.props.moveRow(getRowIndex(target.parentElement) + 1, target.parentElement),
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
        ].filter(Boolean);
    }
}
