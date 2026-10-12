import { Component, onMounted, signal, t, useEffect, useProps } from "@odoo/owl";

export class AutoresizeInput extends Component {
    static template = "mail.AutoresizeInput";
    props = useProps({
        autofocus: t.boolean().optional(false),
        className: t.string().optional(""),
        enabled: t.boolean().optional(true),
        inputClassName: t.string().optional(""),
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

    /**
     * What sizes the box. Never empty, so the box always keeps a line's height even
     * without a value or placeholder.
     */
    get mirrorValue() {
        return this.value() || this.props.placeholder || " ";
    }
}
