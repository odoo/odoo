import { Component, onMounted, signal, t, useEffect, useProps } from "@odoo/owl";

import { useAutoresize } from "@web/core/utils/autoresize";

export class AutoresizeInput extends Component {
    static template = "mail.AutoresizeInput";
    props = useProps({
        autofocus: t.boolean().optional(false),
        className: t.string().optional(""),
        enabled: t.boolean().optional(true),
        inputRef: t.signal(t.instanceOf(HTMLInputElement)).optional(() => signal.ref()),
        onValidate: t.function([t.string()]).optional(() => () => {}),
        placeholder: t.string().optional(""),
        value: t.signal(t.string()),
    });

    setup() {
        super.setup();
        this.inputRef = this.props.inputRef;
        this.value = signal("");
        useEffect(() => this.value.set(this.props.value() || ""));
        this.isFocused = signal(false);
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
                this.value.set(this.props.value() || "");
                this.inputRef().blur();
                break;
        }
    }

    onBlurInput() {
        this.isFocused.set(false);
        this.props.onValidate(this.value());
    }
}
