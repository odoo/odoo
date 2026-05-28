import { Component, onMounted, props, signal, types, useEffect } from "@odoo/owl";

import { useAutoresize } from "@web/core/utils/autoresize";

export class AutoresizeInput extends Component {
    static template = "mail.AutoresizeInput";
    props = props(
        {
            "autofocus?": types.boolean(),
            "className?": types.string(),
            "enabled?": types.boolean(),
            "onValidate?": types.function(),
            "placeholder?": types.string(),
            "value?": types.signal(),
        },
        {
            autofocus: false,
            className: "",
            enabled: true,
            onValidate: () => {},
            placeholder: "",
        }
    );

    setup() {
        super.setup();
        this.value = signal("");
        useEffect(() => this.value.set(this.props.value()));
        this.isFocused = signal(false);
        this.inputRef = signal();
        useAutoresize(this.inputRef);
        onMounted(() => {
            if (this.props.autofocus) {
                this.inputRef().focus();
                this.inputRef().setSelectionRange(-1, -1);
            }
        });
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onKeydownInput(ev) {
        switch (ev.key) {
            case "Enter":
                this.inputRef().blur();
                break;
            case "Escape":
                ev.stopPropagation();
                this.value.set(this.props.value());
                this.inputRef().blur();
                break;
        }
    }

    onBlurInput() {
        this.isFocused.set(false);
        this.props.onValidate(this.value());
    }
}
