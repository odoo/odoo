import { Component, onMounted, props, signal, types, useEffect } from "@odoo/owl";

import { useAutoresize } from "@web/core/utils/autoresize";
import { useRef } from "@web/owl2/utils";

export class AutoresizeInput extends Component {
    static template = "mail.AutoresizeInput";
    props = props(
        {
            "autofocus?": types.boolean(),
            "className?": types.string(),
            "enabled?": types.boolean(),
            "onValidate?": types.function(),
            "placeholder?": types.string(),
            /** @type {import("@odoo/owl").Signal<string|undefined>} */
            value: types.signal(),
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
        useEffect(() => this.value.set(this.props.value() || ""));
        this.isFocused = signal(false);
        this.inputRef = useRef("input");
        useAutoresize(this.inputRef);
        onMounted(() => {
            if (this.props.autofocus) {
                this.inputRef.el.focus();
                this.inputRef.el.setSelectionRange(-1, -1);
            }
        });
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onKeydownInput(ev) {
        switch (ev.key) {
            case "Enter":
                this.inputRef.el.blur();
                break;
            case "Escape":
                ev.stopPropagation();
                this.value.set(this.props.value() || "");
                this.inputRef.el.blur();
                break;
        }
    }

    onBlurInput() {
        this.isFocused.set(false);
        this.props.onValidate(this.value());
    }
}
