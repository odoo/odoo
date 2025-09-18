// @ts-check

/** @module @web/views/kanban/kanban_column_quick_create - Inline quick-create widget for adding new kanban columns (groups) */

import { Component, onPatched, useExternalListener, useRef, useState } from "@odoo/owl";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { useHotkey } from "@web/services/hotkeys/hotkey_hook";

/**
 * Inline quick-create widget for adding new kanban columns (groups).
 *
 * Appears at the end of the kanban board when grouped by a supported field.
 * Supports fold/unfold toggling, Enter-to-validate, Escape-to-close, and
 * closes automatically on outside clicks.
 */
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
        useExternalListener(window, "mousedown", (/** @type {Event} */ ev) => {
            // This target is kept in order to impeach close on outside click behavior if the click
            // has been initiated from the quickcreate root element (mouse selection in an input...)
            this.mousedownTarget = ev.target;
        });
        useExternalListener(
            window,
            "click",
            (/** @type {Event} */ ev) => {
                const target = /** @type {Node} */ (this.mousedownTarget || ev.target);
                const gotClickedInside = this.root.el.contains(target);
                if (!gotClickedInside) {
                    this.fold();
                }
                this.mousedownTarget = null;
            },
            { capture: true },
        );

        // Key Navigation
        useHotkey("escape", () => this.fold());
        onPatched(() => {
            if (this.state.hasInputFocused && !this.props.folded) {
                this.root.el.scrollIntoView({ behavior: "smooth" });
            }
        });
    }

    /** @returns {string} Human-readable label of the group-by field. */
    get relatedFieldName() {
        return this.props.groupByField.string;
    }

    /** Collapse the quick-create input. */
    fold() {
        this.props.onFoldChange(true);
    }

    /** Expand the quick-create input. */
    unfold() {
        this.props.onFoldChange(false);
    }

    /** Submit the input value as a new column title, then reset the input. */
    validate() {
        const inputEl = /** @type {HTMLInputElement} */ (this.inputRef.el);
        const title = inputEl.value.trim();
        if (title.length) {
            this.props.onValidate(title);
            inputEl.value = "";
            inputEl.focus();
            this.state.hasInputFocused = true;
        }
    }

    /**
     * Validate on Enter key press.
     * @param {KeyboardEvent} ev
     */
    onInputKeydown(ev) {
        if (ev.key === "Enter") {
            this.validate();
        }
    }
}
