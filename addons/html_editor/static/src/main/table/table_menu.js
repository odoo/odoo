import { Component, onMounted, onWillUpdateProps, useRef } from "@odoo/owl";
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
        resetTableSize: Function,
        close: Function,
        dropdownState: Object,
        target: { validate: (el) => el.nodeType === Node.ELEMENT_NODE },
        direction: { type: String, optional: true },
    };
    static defaultProps = { direction: "ltr" };
    static components = { Dropdown, DropdownItem };

    setup() {
        this.dropdownRef = useRef("dropdown");
        if (this.props.type === "column") {
            this.isFirst = this.props.target.cellIndex === 0;
            this.isLast = !this.props.target.nextElementSibling;
        } else {
            const tr = this.props.target.parentElement;
            this.isFirst = !tr.previousElementSibling;
            this.isLast = !tr.nextElementSibling;
        }
        this.items = this.props.type === "column" ? this.colItems() : this.rowItems();
        onWillUpdateProps((newProps) => {
            this.updatePosition(newProps);
        });
        onMounted(() => {
            this.overlayEl = this.dropdownRef.el;
            this.updatePosition(this.props);
        });
    }

    get hasCustomSize() {
        return (
            !!this.props.target.closest("tr").style.height ||
            !!this.props.target.closest("td")?.style?.width ||
            !!this.props.target.closest("th")?.style?.width
        );
    }

    updatePosition({ target, type, direction }) {
        if (!this.overlayEl || !target) {
            return;
        }
        const targetRect = target.getBoundingClientRect();
        const container = this.overlayEl.parentElement;
        const containerRect = container.getBoundingClientRect();
        if (type === "column") {
            Object.assign(this.overlayEl.style, {
                top: `${targetRect.top - containerRect.top - this.overlayEl.offsetHeight}px`,
                left: `${targetRect.left - containerRect.left}px`,
                width: `${targetRect.width}px`,
            });
        } else {
            const isLTR = direction === "ltr";
            const inlineStartOffset = isLTR
                ? targetRect.left - containerRect.left
                : containerRect.right - targetRect.right;
            Object.assign(this.overlayEl.style, {
                top: `${targetRect.top - containerRect.top}px`,
                insetInlineStart: `${inlineStartOffset - this.overlayEl.offsetWidth}px`,
                height: `${targetRect.height}px`,
            });
        }
    }
    onSelected(item) {
        item.action(this.props.target);
        this.props.close();
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
            this.hasCustomSize && {
                name: "reset_size",
                icon: "fa-table",
                text: _t("Reset Size"),
                action: (target) => this.props.resetTableSize(target.closest("table")),
            },
        ].filter(Boolean);
    }

    rowItems() {
        return [
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
            {
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
            this.hasCustomSize && {
                name: "reset_size",
                icon: "fa-table",
                text: _t("Reset Size"),
                action: (target) => this.props.resetTableSize(target.closest("table")),
            },
        ].filter(Boolean);
    }
}
