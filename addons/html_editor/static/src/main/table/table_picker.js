import { Component, proxy, t, useListener, useProps } from "@odoo/owl";

export class TablePicker extends Component {
    static template = "html_editor.TablePicker";

    props = useProps({
        direction: t.string(),
        editable: t.customValidator(t.object(), (el) => el.nodeType === Node.ELEMENT_NODE),
        insertTable: t.function(),
        overlay: t.object(),
    });

    state = proxy({
        cols: 3,
        rows: 3,
    });

    setup() {
        useListener(
            this.props.editable.ownerDocument,
            "keydown",
            (ev) => {
                ev.stopPropagation();
                const key = ev.key;
                const isRTL = this.props.direction === "rtl";
                switch (key) {
                    case "Enter":
                        ev.preventDefault();
                        this.insertTable();
                        break;
                    case "ArrowUp":
                        ev.preventDefault();
                        if (this.state.rows > 1) {
                            this.state.rows -= 1;
                        }
                        break;
                    case "ArrowDown":
                        this.state.rows += 1;
                        ev.preventDefault();
                        break;
                    case "ArrowLeft":
                        ev.preventDefault();
                        if (isRTL) {
                            this.state.cols += 1;
                        } else {
                            if (this.state.cols > 1) {
                                this.state.cols -= 1;
                            }
                        }
                        break;
                    case "ArrowRight":
                        ev.preventDefault();
                        if (isRTL) {
                            if (this.state.cols > 1) {
                                this.state.cols -= 1;
                            }
                        } else {
                            this.state.cols += 1;
                        }
                        break;
                    default:
                        ev.stopImmediatePropagation();
                        this.props.overlay.close();
                        break;
                }
            },
            { capture: true }
        );
    }

    updateSize(cols, rows) {
        this.state.cols = cols;
        this.state.rows = rows;
    }

    insertTable() {
        this.props.insertTable({ cols: this.state.cols, rows: this.state.rows });
        this.props.overlay.close();
    }
}
