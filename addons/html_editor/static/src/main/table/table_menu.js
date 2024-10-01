import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";

export class TableMenu extends Component {
    static template = "html_editor.TableMenu";
    static props = {
        type: String, // column or row
        dispatch: Function,
        overlay: Object,
        dropdownState: Object,
        target: { validate: (el) => el.nodeType === Node.ELEMENT_NODE },
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
        }
        this.items = this.props.type === "column" ? this.colItems() : this.rowItems();
    }

    get hasCustomSize() {
        return (
            !!this.props.target.closest("tr").style.height ||
            !!this.props.target.closest("td").style.width
        );
    }

    onSelected(item) {
        item.action(this.props.target);
        this.props.overlay.close();
    }

    colItems() {
        const ltr = this.props.direction === "ltr";
        return [
            !this.isFirst && {
                name: "move_left",
                icon: "fa-chevron-left disabled",
                text: ltr ? _t("Move left") : _t("Move right"),
                action: this.moveColumn.bind(this, "left"),
            },
            !this.isLast && {
                name: "move_right",
                icon: "fa-chevron-right",
                text: ltr ? _t("Move right") : _t("Move left"),
                action: this.moveColumn.bind(this, "right"),
            },
            {
                name: "insert_left",
                icon: "fa-plus",
                text: ltr ? _t("Insert left") : _t("Insert right"),
                action: this.insertColumn.bind(this, "before"),
            },
            {
                name: "insert_right",
                icon: "fa-plus",
                text: ltr ? _t("Insert right") : _t("Insert left"),
                action: this.insertColumn.bind(this, "after"),
            },
            {
                name: "delete",
                icon: "fa-trash",
                text: _t("Delete"),
                action: this.deleteColumn.bind(this),
            },
            this.hasCustomSize && {
                name: "reset_size",
                icon: "fa-table",
                text: _t("Reset Size"),
                action: this.resetSize.bind(this),
            },
        ].filter(Boolean);
    }

    rowItems() {
        return [
            !this.isFirst && {
                name: "move_up",
                icon: "fa-chevron-up",
                text: _t("Move up"),
                action: this.moveRow.bind(this, "up"),
            },
            !this.isLast && {
                name: "move_down",
                icon: "fa-chevron-down",
                text: _t("Move down"),
                action: this.moveRow.bind(this, "down"),
            },
            {
                name: "insert_above",
                icon: "fa-plus",
                text: _t("Insert above"),
                action: this.insertRow.bind(this, "before"),
            },
            {
                name: "insert_below",
                icon: "fa-plus",
                text: _t("Insert below"),
                action: this.insertRow.bind(this, "after"),
            },
            {
                name: "delete",
                icon: "fa-trash",
                text: _t("Delete"),
                action: this.deleteRow.bind(this),
            },
            this.hasCustomSize && {
                name: "reset_size",
                icon: "fa-table",
                text: _t("Reset Size"),
                action: this.resetSize.bind(this),
            },
        ].filter(Boolean);
    }

    moveColumn(position, target) {
        this.props.dispatch("MOVE_COLUMN", { position, cell: target });
    }

    insertColumn(position, target) {
        this.props.dispatch("ADD_COLUMN", { position, reference: target });
    }

    deleteColumn(target) {
        this.props.dispatch("REMOVE_COLUMN", { cell: target });
    }

    moveRow(position, target) {
        this.props.dispatch("MOVE_ROW", { position, row: target.parentElement });
    }

    insertRow(position, target) {
        this.props.dispatch("ADD_ROW", { position, reference: target.parentElement });
    }

    deleteRow(target) {
        this.props.dispatch("REMOVE_ROW", { row: target.parentElement });
    }

    resetSize(target) {
        this.props.dispatch("RESET_SIZE", { table: target.closest("table") });
    }
}
