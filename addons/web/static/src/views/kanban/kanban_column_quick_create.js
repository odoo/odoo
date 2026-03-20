import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { useAutofocus, useService } from "@web/core/utils/hooks";

import { Component, useExternalListener, useState, useRef, onPatched } from "@odoo/owl";

export class KanbanColumnQuickCreate extends Component {
    static template = "web.KanbanColumnQuickCreate";
    static props = {
        onFoldChange: Function,
        onValidate: Function,
        folded: Boolean,
        groupByField: Object,
    };

    setup() {
        this.dialog = useService("dialog");
        this.root = useRef("root");
        this.state = useState({
            hasInputFocused: false,
        });

        useAutofocus();
        this.inputRef = useRef("autofocus");

        // Close on outside click
        useExternalListener(window, "mousedown", (/** @type {MouseEvent} */ ev) => {
            // This target is kept in order to impeach close on outside click behavior if the click
            // has been initiated from the quickcreate root element (mouse selection in an input...)
            this.mousedownTarget = ev.target;
        });
        useExternalListener(
            window,
            "click",
            (/** @type {MouseEvent} */ ev) => {
                const target = this.mousedownTarget || ev.target;
                const gotClickedInside = this.root.el.contains(target);
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
                this.root.el.scrollIntoView({ behavior: "smooth" });
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
        const title = this.inputRef.el.value.trim();
        if (title.length) {
            this.props.onValidate(title);
            this.inputRef.el.value = "";
            this.inputRef.el.focus();
            this.state.hasInputFocused = true;
        }
    }

    onInputKeydown(ev) {
        if (ev.key === "Enter") {
            this.validate();
        }
    }
}
