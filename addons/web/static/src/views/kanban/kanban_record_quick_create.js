/** @odoo-module */
import { useService } from "@web/core/utils/hooks";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { FormRenderer } from "@web/views/form/form_renderer";

const { Component, onMounted, useExternalListener, useState, useRef } = owl;

const ACTION_SELECTORS = [
    ".o_kanban_quick_add",
    ".o_kanban_load_more button",
    ".o-kanban-button-new",
];

export class KanbanRecordQuickCreate extends Component {
    setup() {
        this.uiService = useService("ui");
        this.rootRef = useRef("root");
        this.state = useState({ disabled: false });
        onMounted(() => {
            this.uiActiveElement = this.uiService.activeElement;
        });
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
                if (this.uiActiveElement !== this.uiService.activeElement) {
                    // this component isn't in the current active element -> do nothing
                    return;
                }
                const target = this.mousedownTarget || ev.target;
                const gotClickedOutside = !this.rootRef.el.contains(target);
                if (gotClickedOutside) {
                    let force = false;
                    for (const selector of ACTION_SELECTORS) {
                        const closestEl = target.closest(selector);
                        if (closestEl) {
                            force = true;
                            break;
                        }
                    }
                    this.cancel(force);
                }
                this.mousedownTarget = null;
            },
            { capture: true }
        );

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
