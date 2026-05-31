import { useLayoutEffect, useRef, useState } from "@web/owl2/utils";
import { _t } from "@web/core/l10n/translation";
import { Component, onMounted, onPatched } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { computeM2OProps, extractData, Many2One } from "@web/views/fields/many2one/many2one";
import {
    extractM2OFieldProps,
    m2oSupportedOptions,
    Many2OneField,
} from "@web/views/fields/many2one/many2one_field";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { getFieldDomain } from "@web/model/relational_model/utils";
import { useInputField } from "@web/views/fields/input_field_hook";
import { useAutoresize } from "@web/core/utils/autoresize";

// Simulates a single keyboard action on a string respecting the current
// selection — used to seed pendingText on keydown before preventDefault.
function applyKeyToValue(value, start, end, key) {
    const s = start ?? value.length;
    const e = end ?? value.length;
    if (key.length === 1) {
        return value.slice(0, s) + key + value.slice(e);
    }
    if (key === "Backspace") {
        return s !== e
            ? value.slice(0, s) + value.slice(e)
            : s > 0
            ? value.slice(0, s - 1) + value.slice(s)
            : value;
    }
    if (key === "Delete") {
        return s !== e
            ? value.slice(0, s) + value.slice(e)
            : value.slice(0, s) + value.slice(s + 1);
    }
    return value;
}

// Thin AutoComplete subclass that notifies the parent whenever displayOptions
// (isOpened && hasOptions) actually changes — firing on open() before results
// are known would show the caret even when no results come back.
class OpenAwareAutoComplete extends AutoComplete {
    static props = {
        ...AutoComplete.props,
        onOpenChange: { type: Function, optional: true },
    };

    setup() {
        super.setup();
        this._lastDisplayOptions = false;
        onPatched(() => {
            const val = this.displayOptions;
            if (val !== this._lastDisplayOptions) {
                this._lastDisplayOptions = val;
                this.props.onOpenChange?.(val);
            }
        });
    }
}

// Combined-input autocomplete: no No-records / Start-typing suggestions,
// dropdown opens on typing only (not on bare click/focus).
// showCaretWhenValue: pass true when an M2O option is already selected so the
// caret stays visible even when the dropdown is closed (affordance to re-open).
export class M2OAndTextAutocomplete extends Many2XAutocomplete {
    static template = "web.M2OAndTextAutocomplete";
    static components = {
        ...Many2XAutocomplete.components,
        AutoComplete: OpenAwareAutoComplete,
    };
    static props = {
        ...Many2XAutocomplete.props,
        onBlur: { type: Function, optional: true },
        showCaretWhenValue: { type: Boolean, optional: true },
    };

    setup() {
        super.setup();
        this.caretState = useState({ isOpen: false });
    }

    get autoCompleteProps() {
        return {
            ...super.autoCompleteProps,
            onBlur: ({ inputValue }) => {
                this.caretState.isOpen = false;
                this.props.onBlur?.({ inputValue });
            },
            searchOnInputClick: false,
            onOpenChange: (isOpen) => {
                this.caretState.isOpen = isOpen;
            },
        };
    }

    addNoRecordsSuggestion() {
        return false;
    }

    addStartTypingSuggestion() {
        return false;
    }
}

// Uses M2OAndTextAutocomplete so Create options are suppressed.
// Passes showCaretWhenValue so the caret is always visible when an M2O is
// selected (user can see it's a dropdown and open it again).
class RestrictedMany2One extends Many2One {
    static components = {
        ...Many2One.components,
        Many2XAutocomplete: M2OAndTextAutocomplete,
    };

    get many2XAutocompleteProps() {
        return {
            ...super.many2XAutocompleteProps,
            showCaretWhenValue: true,
        };
    }
}

export class M2OAndTextField extends Component {
    static template = "web.M2OAndTextField";
    static components = { M2OAndTextAutocomplete, Many2One, RestrictedMany2One };
    static props = {
        ...Many2OneField.props,
        textFieldName: { type: String },
        required: { type: Boolean },
    };

    setup() {
        this.rootRef = useRef("root");
        this.textAreaRef = useRef("textArea");
        const initialText = this.props.record.data[this.props.textFieldName] || "";
        this.state = useState({
            // Initialized from the record so rows with pre-existing multi-line text
            // open straight into the textarea without a flicker.
            // Only meaningful in NOT-required mode.
            showStacked: !this.props.required && initialText.includes("\n"),
            // Optimistic flag: true from when the user clears the M2O until
            // record.update resolves, so hasM2OSelected flips immediately.
            m2oClearedLocally: false,
            // Live value carried from the textarea into the combined input when
            // switching mode without a blur/commit in between.
            pendingText: null,
        });

        useInputField({
            ref: this.textAreaRef,
            fieldName: this.props.textFieldName,
            getValue: () => this.textValue,
        });
        useAutoresize(this.textAreaRef);

        onMounted(() => {
            if (this.props.record.isNew) {
                this.rootRef.el?.querySelector("input")?.focus();
            }
        });

        useLayoutEffect(
            () => {
                // Skip when the clear was user-initiated (m2oClearedLocally) —
                // that path is handled in restrictedM2OProps.update.
                if (!this.props.record.data[this.props.name] && !this.state.m2oClearedLocally) {
                    const text = this.props.record.data[this.props.textFieldName] || "";
                    this.state.showStacked = !this.props.required && text.includes("\n");
                }
            },
            () => [this.props.record.data[this.props.name]]
        );

        // _protectPendingText: raised while the M2O keydown handler awaits the
        // server onchange. The onchange may reset textFieldName to "" — we must
        // not let that wipe the combined-input value the user is actively editing.
        useLayoutEffect(
            () => {
                if (!this._protectPendingText) {
                    this.state.pendingText = null;
                }
                const text = this.props.record.data[this.props.textFieldName] || "";
                if (!this.props.required && text.includes("\n")) {
                    this.state.showStacked = true;
                } else if (this.state.showStacked && !this.props.record.data[this.props.name]) {
                    this.state.showStacked = false;
                    requestAnimationFrame(() => {
                        if (this.rootRef.el?.contains(document.activeElement)) {
                            this.rootRef.el.querySelector("input")?.focus();
                        }
                    });
                }
            },
            () => [this.props.record.data[this.props.textFieldName]]
        );

        // onPatched fires synchronously in the same microtask as the state
        // mutation, so focus moves without triggering blur/change on the textarea
        // (which would call record.update and exit list edit mode).
        onPatched(() => {
            if (this._focusCombinedInput) {
                this._focusCombinedInput = false;
                const input = this.rootRef.el?.querySelector("input");
                if (input) {
                    input.focus();
                    // Place cursor at end; browsers select-all on programmatic focus.
                    input.setSelectionRange(input.value.length, input.value.length);
                    // Open the autocomplete dropdown immediately without an extra keystroke.
                    input.dispatchEvent(new InputEvent("input", { bubbles: true }));
                }
            }
        });
    }

    get textVisible() {
        return this.props.required ? !!this.props.record.data[this.props.name] : true;
    }

    get textValue() {
        return this.props.record.data[this.props.textFieldName] || "";
    }

    get m2oDisplayName() {
        const m2oValue = this.props.record.data[this.props.name];
        return m2oValue ? m2oValue.display_name || "" : "";
    }

    // Accounts for the optimistic m2oClearedLocally flag.
    get hasM2OSelected() {
        return !this.state.m2oClearedLocally && !!this.props.record.data[this.props.name];
    }

    get m2oProps() {
        const { record, name, textFieldName, readonly } = this.props;
        const p = computeM2OProps(this.props);
        return {
            ...p,
            // In display mode: plain span so clicking the cell enters row-edit
            // mode instead of navigating to the form view.
            canOpen: !readonly,
            update: async (value, options) => {
                await record.update({ [name]: value, [textFieldName]: "" }, options);
                if (this.props.required && !readonly && value) {
                    requestAnimationFrame(() => this.textAreaRef.el?.focus());
                }
            },
        };
    }

    get restrictedM2OProps() {
        const { record, name, textFieldName } = this.props;
        const p = computeM2OProps(this.props);
        return {
            ...p,
            canCreate: false,
            canCreateEdit: false,
            canOpen: true,
            canQuickCreate: false,
            update: async (value, options) => {
                if (!value) {
                    // Flip immediately so the template re-renders before the server
                    // onchange — no roundtrip needed to switch modes.
                    this.state.m2oClearedLocally = true;
                    this.state.showStacked = false;
                }
                await record.update({ [name]: value, [textFieldName]: "" }, options);
                this.state.m2oClearedLocally = false;
            },
        };
    }

    get m2oAndTextAutocompleteProps() {
        const { record, name: m2oFieldName, textFieldName } = this.props;
        return {
            activeActions: {
                create: false,
                createEdit: false,
                write: !!this.props.canWrite,
            },
            context: this.props.context || {},
            fieldString: this.props.string || record.fields[m2oFieldName].string || "",
            getDomain: () => getFieldDomain(record, m2oFieldName, this.props.domain),
            id: this.props.id,
            nameCreateField: this.props.nameCreateField,
            // Use the text field's label so the placeholder is relevant for free-text entry.
            placeholder: this.props.placeholder || record.fields[textFieldName]?.string || "",
            quickCreate: null,
            resModel: record.fields[m2oFieldName].relation,
            searchLimit: this.props.searchLimit,
            searchThreshold: this.props.searchThreshold ?? 0,
            update: (records, options) => this.updateM2OAndText(records, options),
            value: this.state.pendingText ?? this.textValue,
            onBlur: ({ inputValue }) => this.onCombinedInputBlur(inputValue),
        };
    }

    // The text field is intentionally NOT auto-filled with the M2O display name.
    async updateM2OAndText(records, options = {}) {
        const data = Array.isArray(records) ? records?.[0] : records;
        const idNamePair = data ? extractData(data) : false;
        await this.props.record.update(
            {
                [this.props.name]: idNamePair,
                ...(idNamePair ? { [this.props.textFieldName]: "" } : {}),
            },
            options
        );
        if (idNamePair) {
            requestAnimationFrame(() => this.textAreaRef.el?.focus());
        }
    }

    // AutoComplete guarantees this is NOT called when an option was clicked
    // (ignoreBlur is true then), so there is no race with updateM2OAndText.
    async onCombinedInputBlur(inputValue) {
        this._protectPendingText = false;
        if (inputValue !== this.textValue) {
            await this.props.record.update({ [this.props.textFieldName]: inputValue });
        } else {
            // No record update → useLayoutEffect won't run → clear pendingText manually.
            this.state.pendingText = null;
        }
    }

    onTextareaInput(ev) {
        if (this.hasM2OSelected || ev.target.value.includes("\n")) {
            return;
        }
        // Set _focusCombinedInput before mutating state so onPatched moves focus
        // without triggering blur/change on the textarea (which would call
        // record.update and exit list edit mode).
        this._focusCombinedInput = true;
        this.state.pendingText = ev.target.value;
        this.state.showStacked = false;
    }

    onKeydown(ev) {
        // When an M2O is selected and the user types/backspaces in the M2O input,
        // immediately switch to combined-input mode before the async record.update.
        if (
            !this.props.readonly &&
            this.hasM2OSelected &&
            ev.target.tagName === "INPUT" &&
            !ev.ctrlKey &&
            !ev.metaKey &&
            !ev.altKey &&
            (ev.key.length === 1 || ev.key === "Backspace" || ev.key === "Delete")
        ) {
            ev.preventDefault();
            // Fall back to the M2O display name when the autocomplete input is
            // empty (before the user has typed into it after selecting).
            const baseText = ev.target.value || this.m2oDisplayName;
            const s = ev.target.value ? ev.target.selectionStart : baseText.length;
            const e = ev.target.value ? ev.target.selectionEnd : baseText.length;
            const newText = applyKeyToValue(baseText, s, e, ev.key);
            // Raise the guard BEFORE updating state so the useLayoutEffect that fires
            // when the M2O onchange resets textFieldName does NOT clear pendingText.
            this._protectPendingText = true;
            this.state.m2oClearedLocally = true;
            this.state.showStacked = false;
            this.state.pendingText = newText;
            this._focusCombinedInput = true;
            // Clear only the M2O now; commit the text field in .then() so the
            // server onchange cannot overwrite it.
            this.props.record.update({ [this.props.name]: false }).then(() => {
                this.state.m2oClearedLocally = false;
                this._protectPendingText = false;
                // Read the live DOM value — the user may have typed more after the switch.
                const input = this.rootRef.el?.querySelector("input");
                const valueToCommit = input?.value ?? newText;
                if (valueToCommit !== this.textValue) {
                    this.props.record.update({ [this.props.textFieldName]: valueToCommit });
                } else {
                    this.state.pendingText = null;
                }
            });
            return;
        }

        // Textarea: UP at the very start → focus the M2O input above.
        if (
            ev.key === "ArrowUp" &&
            ev.target.tagName === "TEXTAREA" &&
            ev.target.selectionStart === 0 &&
            !this.props.readonly &&
            (this.hasM2OSelected || (this.props.required && this.textVisible))
        ) {
            ev.preventDefault();
            this.rootRef.el?.querySelector("input")?.focus();
            return;
        }

        // AutoComplete only stopPropagation's Enter when an option is active; an
        // unhandled Enter bubbles here, signalling the user confirmed free text.
        if (ev.key !== "Enter" || ev.target.tagName === "TEXTAREA") {
            return;
        }
        if (
            this.props.readonly ||
            this.props.required ||
            this.hasM2OSelected ||
            this.state.showStacked
        ) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        this.onCombinedInputEnter(ev.target.value || "");
    }

    // Sets showStacked immediately (before the async record.update) so the
    // textarea appears right away. Appends "\n" so the cursor lands on a fresh line.
    async onCombinedInputEnter(inputValue) {
        if (!inputValue) {
            return;
        }
        this.state.showStacked = true;
        const newValue = inputValue + "\n";
        if (newValue !== this.textValue) {
            await this.props.record.update({ [this.props.textFieldName]: newValue });
        }
        requestAnimationFrame(() => {
            const el = this.textAreaRef.el;
            if (el) {
                el.focus();
                el.setSelectionRange(el.value.length, el.value.length);
            }
        });
    }
}

registry.category("fields").add("m2o_and_text_field", {
    component: M2OAndTextField,
    displayName: _t("Many2one with Text"),
    supportedTypes: ["many2one"],
    extractProps: (staticInfo, dynamicInfo) => ({
        ...extractM2OFieldProps(staticInfo, dynamicInfo),
        textFieldName: staticInfo.options.text_field || "",
        required: dynamicInfo.required,
    }),
    supportedOptions: [
        ...m2oSupportedOptions,
        {
            label: _t("Text field"),
            name: "text_field",
            type: "field",
            availableTypes: ["char", "text"],
        },
    ],
});
