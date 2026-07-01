import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { useAutofocus, useService } from "@web/core/utils/hooks";

import { Component, onPatched, proxy, signal, useListener } from "@odoo/owl";

export class KanbanColumnQuickCreate extends Component {
    static template = "web.KanbanColumnQuickCreate";
    static props = {
        onFoldChange: Function,
        onValidate: Function,
        folded: Boolean,
        groupByField: Object,
    };

    root = signal(null);
    inputRef = signal(null);

    setup() {
        this.dialog = useService("dialog");
        this.state = proxy({
            hasInputFocused: false,
        });

        useAutofocus({ ref: this.inputRef });

        // Close on outside click
        useListener(window, "mousedown", (/** @type {MouseEvent} */ ev) => {
            // This target is kept in order to impeach close on outside click behavior if the click
            // has been initiated from the quickcreate root element (mouse selection in an input...)
            this.mousedownTarget = ev.target;
        });
        useListener(
            window,
            "click",
            (/** @type {MouseEvent} */ ev) => {
                if (!this.root()) {
                    return;
                }
                const target = this.mousedownTarget || ev.target;
                const gotClickedInside = this.root().contains(target);
                if (!gotClickedInside) {
                    this.fold();
                }
                this.mousedownTarget = null;
            },
            { capture: true }
        );

        // Key Navigation
        useHotkey("escape", () => this.fold());
        onPatched(() => {
            if (this.state.hasInputFocused && !this.props.folded) {
                this.root().scrollIntoView({ behavior: "smooth" });
            }
        });
    }

    get relatedFieldName() {
        return this.props.groupByField.string;
    }

    fold() {
        this.props.onFoldChange(true);
    }

    unfold() {
        this.props.onFoldChange(false);
    }

    validate() {
        const title = this.inputRef().value.trim();
        if (title.length) {
            this.props.onValidate(title);
            this.inputRef().value = "";
            this.inputRef().focus();
            this.state.hasInputFocused = true;
        }
    }

    onInputKeydown(ev) {
        if (ev.key === "Enter") {
            this.validate();
        }
    }
}
