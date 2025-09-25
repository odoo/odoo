import { closestElement } from "@html_editor/utils/dom_traversal";
import { Component, onMounted, onWillUnmount, useExternalListener, useRef } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { TableDragDrop } from "./table_drag_drop";

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
        addStep: Function,
        resetRowHeight: Function,
        resetColumnWidth: Function,
        resetTableSize: Function,
        clearColumnContent: Function,
        clearRowContent: Function,
        overlay: Object,
        createOverlay: { type: Function, optional: true },
        dropdownState: Object,
        target: { validate: (el) => el.nodeType === Node.ELEMENT_NODE },
        document: { validate: (p) => p.nodeType === Node.DOCUMENT_NODE },
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
            const table = closestElement(this.props.target, "table");
            const rect =
                this.props.type === "row"
                    ? this.props.target.parentElement.getBoundingClientRect()
                    : this.props.target.getBoundingClientRect();
            // Create and open the TableDragDrop overlay.
            this.tableDragDropOverlay = this.props.createOverlay(TableDragDrop);
            this.tableDragDropOverlay.open({
                target: this.props.target,
                props: {
                    overlayRect: {
                        top: rect.top,
                        left: rect.left,
                        width: rect.width,
                        height:
                            this.props.type === "row"
                                ? rect.height
                                : table.getBoundingClientRect().height,
                    },
                    pointerPos: { x: ev.clientX, y: ev.clientY },
                    type: this.props.type,
                    close: () => this.tableDragDropOverlay.close(),
                    turnIntoRow: this.props.turnIntoRow,
                    turnIntoHeader: this.props.turnIntoHeader,
                    addStep: this.props.addStep,
                    target: this.props.target,
                    document: this.props.document,
                },
            });
        }, 100); // long press threshold
    }

    onPointerUp() {
        // Cancel long-press to prevent overlay
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
                action: this.props.moveColumn.bind(this, "left"),
            },
            !this.isLast && {
                name: "move_right",
                icon: "fa-chevron-right",
                text: ltr ? _t("Move right") : _t("Move left"),
                action: this.props.moveColumn.bind(this, "right"),
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
        return [
            this.isFirst &&
                !this.isTableHeader && {
                    name: "make_header",
                    icon: "fa-th-large",
                    text: _t("Turn into header"),
                    action: (target) => {
                        this.props.turnIntoHeader(target.parentElement);
                        this.props.addStep();
                    },
                },
            this.isFirst &&
                this.isTableHeader && {
                    name: "remove_header",
                    icon: "fa-table",
                    text: _t("Turn into row"),
                    action: (target) => {
                        this.props.turnIntoRow(target.parentElement);
                        this.props.addStep();
                    },
                },
            !this.isFirst && {
                name: "move_up",
                icon: "fa-chevron-up",
                text: _t("Move up"),
                action: (target) => this.props.moveRow("up", target.parentElement),
            },
            !this.isLast && {
                name: "move_down",
                icon: "fa-chevron-down",
                text: _t("Move down"),
                action: (target) => this.props.moveRow("down", target.parentElement),
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
        ].filter(Boolean);
    }
}
