import { useExternalListener } from "@web/owl2/utils";
import { Component, signal, useEffect } from "@odoo/owl";

export class MobileTablePicker extends Component {
    static template = "html_editor.MobileTablePicker";
    static props = {
        insertTable: Function,
        close: Function,
        editable: {
            validate: (el) => el.nodeType === Node.ELEMENT_NODE,
        },
    };

    rowCountRef = signal(null);
    columnCountRef = signal(null);
    rowCount = signal(3);
    columnCount = signal(3);

    setup() {
        useEffect(() => {
            const el = this.rowCountRef();
            if (el) {
                el.focus();
            }
        });
        useExternalListener(
            this.props.editable.ownerDocument,
            "keydown",
            (ev) => {
                ev.stopPropagation();
                if (!ev.target.matches(".o-we-tablesizepopover input")) {
                    return;
                }
                switch (ev.key) {
                    case "Enter":
                        ev.preventDefault();
                        this.insertTable();
                        break;
                    case "Escape":
                        ev.preventDefault();
                        this.props.close();
                        break;
                }
            },
            { capture: true }
        );
    }

    updateSize() {
        this.rowCount.set(parseInt(this.rowCountRef().value));
        this.columnCount.set(parseInt(this.columnCountRef().value));
    }

    insertTable() {
        if (this.columnCount() > 0 && this.rowCount() > 0) {
            this.props.insertTable({ cols: this.columnCount(), rows: this.rowCount() });
            this.props.close();
        }
    }

    onApply() {
        this.insertTable();
    }

    onDiscard() {
        this.props.close();
    }
}
