/* @odoo-module */

import { Component, useRef, useState, onWillUpdateProps, onMounted } from "@odoo/owl";

import { useAutoresize } from "@web/core/utils/autoresize";

export class AutoresizeInput extends Component {
    static template = "mail.AutoresizeInput";
    static props = {
        autofocus: { type: Boolean, optional: true },
        className: { type: String, optional: true },
        enabled: { optional: true },
        onValidate: { type: Function, optional: true },
        placeholder: { type: String, optional: true },
        value: { type: String, optional: true },
    };
    static defaultProps = {
        autofocus: false,
        className: "",
        enabled: true,
        onValidate: () => {},
        placeholder: "",
    };

    setup() {
        this.state = useState({
            value: this.props.value,
            isFocused: false,
        });
        this.inputRef = useRef("input");
        onWillUpdateProps((nextProps) => {
            if (this.props.value !== nextProps.value) {
                this.state.value = nextProps.value;
            }
        });
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
                this.state.value = this.props.value;
                this.inputRef.el.blur();
                break;
        }
    }

    onBlurInput() {
        this.state.isFocused = false;
        this.props.onValidate(this.state.value);
    }
}
