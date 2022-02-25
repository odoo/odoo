/** @odoo-module */
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { FormRenderer } from "@web/views/form/form_renderer";

const { Component, useExternalListener, useState, useRef } = owl;

export class KanbanRecordQuickCreate extends Component {
    setup() {
        this.root = useRef("root");
        this.state = useState({ disabled: false });

        // Close on outside click
        useExternalListener(window, "mousedown", (/** @type {MouseEvent} */ ev) => {
            // This target is kept in order to impeach close on outside click behavior if the click
            // has been initiated from the quickcreate root element (mouse selection in an input...)
            this.mousedownTarget = ev.target;
        });
        useExternalListener(window, "click", (/** @type {MouseEvent} */ ev) => {
            const target = this.mousedownTarget || ev.target;
            const gotClickedInside = this.root.el.contains(target);
            if (!gotClickedInside) {
                this.cancel(false);
            }
            this.mousedownTarget = null;
        });

        // Key Navigation
        // FIXME ? Maybe it will also validate even if enter is pressed outside of the quick create machin
        useHotkey("enter", () => this.validate("add"), { bypassEditableProtection: true });
        useHotkey("escape", () => this.cancel(true));
    }

    /** @param {boolean} force */
    cancel(force) {
        this.props.onCancel(force);
    }

    /** @param {"add" | "edit"} mode */
    async validate(mode) {
        if (this.state.disabled) {
            return;
        }
        this.state.disabled = true;
        await this.props.onValidate(mode);
        this.state.disabled = false;
    }
}
KanbanRecordQuickCreate.template = "web.KanbanRecordQuickCreate";
KanbanRecordQuickCreate.components = { FormRenderer };
