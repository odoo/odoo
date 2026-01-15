import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { useEffect } from "@odoo/owl";

export class AutoCompleteWithPages extends AutoComplete {
    static props = {
        ...AutoComplete.props,
        targetDropdown: { type: HTMLElement },
    };
    static template = "website.AutoCompleteWithPages";

    setup() {
        super.setup();
        useEffect(
            (input, inputRef) => {
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
                return () => {
                    input.removeEventListener("blur", targetBlur);
                    input.removeEventListener("click", targetClick);
                    input.removeEventListener("change", targetChange);
                    input.removeEventListener("input", targetInput);
                    input.removeEventListener("keydown", targetKeydown);
                    input.removeEventListener("focus", targetFocus);
                };
            },
            () => [this.targetDropdown, this.inputRef.el]
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
