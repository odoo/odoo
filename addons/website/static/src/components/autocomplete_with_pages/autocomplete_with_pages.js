import { props, t, useListener } from "@odoo/owl";
import { AutoComplete, autoCompleteProps } from "@web/core/autocomplete/autocomplete";

export class AutoCompleteWithPages extends AutoComplete {
    props = props({
        ...autoCompleteProps,
        targetDropdown: t.instanceOf(HTMLElement),
    });
    static template = "website.AutoCompleteWithPages";

    setup() {
        super.setup();
        // targetDropdown outlives this component; a trailing event on teardown can fire when inputRef.el is already null.
        const whenMounted = (handler) => (ev) => {
            if (this.inputRef.el) {
                handler.call(this, ev);
            }
        };
        useListener(() => this.targetDropdown, "blur", whenMounted(this.onInputBlur));
        useListener(() => this.targetDropdown, "click", whenMounted(this._syncInputClick));
        useListener(() => this.targetDropdown, "change", whenMounted(this.onInputChange));
        useListener(() => this.targetDropdown, "input", whenMounted(this._syncInputValue));
        useListener(() => this.targetDropdown, "keydown", whenMounted(this.onInputKeydown));
        useListener(() => this.targetDropdown, "focus", whenMounted(this.onInputFocus));
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
