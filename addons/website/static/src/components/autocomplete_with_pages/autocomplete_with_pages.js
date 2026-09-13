/** @odoo-module native */
import { useEffect } from "@odoo/owl";
import { AutoComplete } from "@web/components/autocomplete";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";

const log = makeLogger("website.component.autocomplete_with_pages");

export class AutoCompleteWithPages extends AutoComplete {
    static props = {
        ...AutoComplete.props,
        targetDropdown: { type: HTMLElement },
    };
    static template = "website.AutoCompleteWithPages";

    setup() {
        super.setup();
        useLifecycleLog(log);
        useEffect(
            (input, inputRef) => {
                log.lifecycle("target input listeners attached", () => ({
                    synced: Boolean(inputRef),
                }));
                if (inputRef) {
                    inputRef.value = input.value;
                }
                const targetBlur = this.onInputBlur.bind(this);
                const targetClick = this._syncInputClick.bind(this);
                const targetChange = this.onInputChange.bind(this);
                const targetInput = this._syncInputValue.bind(this);
                const targetKeydown = this.onInputKeydown.bind(this);
                const targetFocus = this.onInputFocus.bind(this);
                input.addEventListener("blur", targetBlur);
                input.addEventListener("click", targetClick);
                input.addEventListener("change", targetChange);
                input.addEventListener("input", targetInput);
                input.addEventListener("keydown", targetKeydown);
                input.addEventListener("focus", targetFocus);
                if (input.ownerDocument.activeElement === input && input.value) {
                    // typing began before the listeners existed (the picker
                    // mounts its autocomplete after its own mount): the
                    // value already typed deserves the suggestions the next
                    // keystroke would bring
                    log.logic("target input focused before attach: syncing value");
                    this._syncInputValue();
                }
                return () => {
                    log.lifecycle("target input listeners removed");
                    input.removeEventListener("blur", targetBlur);
                    input.removeEventListener("click", targetClick);
                    input.removeEventListener("change", targetChange);
                    input.removeEventListener("input", targetInput);
                    input.removeEventListener("keydown", targetKeydown);
                    input.removeEventListener("focus", targetFocus);
                };
            },
            () => [this.targetDropdown, this.inputRef.el],
        );
    }

    get targetDropdown() {
        return this.props.targetDropdown;
    }

    _syncInputClick(ev) {
        ev.stopPropagation();
        this.onInputClick(ev);
    }

    async _syncInputValue() {
        if (this.inputRef.el) {
            this.inputRef.el.value = this.targetDropdown.value;
            this.onInput();
        }
    }

    /**
     * @override
     */
    onInputFocus(ev) {
        this.targetDropdown.setSelectionRange(0, this.targetDropdown.value.length);
        this.props.onFocus(ev);
    }
}
