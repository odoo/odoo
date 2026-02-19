import { Component, useEffect, useExternalListener, useRef, useState } from "@odoo/owl";

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
        useEffect(
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
        this.props.insertTable({ cols: this.state.columnCount, rows: this.state.rowCount });
        this.props.close();
    }

    onApply() {
        this.insertTable();
    }

    onDiscard() {
        this.props.close();
    }
}
