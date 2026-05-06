import { useExternalListener, useLayoutEffect, useRef, useState } from "@web/owl2/utils";
import { Component } from "@odoo/owl";

export class MobileTablePicker extends Component {
    static template = "html_editor.MobileTablePicker";
    static props = {
        insertTable: Function,
        close: Function,
        editable: {
            validate: (el) => el.nodeType === Node.ELEMENT_NODE,
        },
    };

    setup() {
        this.state = useState({
            rowCount: 3,
            columnCount: 3,
        });
        this.rowCountRef = useRef("rowCount");
        this.columnCountRef = useRef("columnCount");
        useLayoutEffect(
            (el) => {
                if (el) {
                    el.focus();
                }
            },
            () => [this.rowCountRef.el]
        );
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
        this.state.rowCount = parseInt(this.rowCountRef.el.value);
        this.state.columnCount = parseInt(this.columnCountRef.el.value);
    }

    insertTable() {
        if (this.state.columnCount > 0 && this.state.rowCount > 0) {
            this.props.insertTable({ cols: this.state.columnCount, rows: this.state.rowCount });
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
