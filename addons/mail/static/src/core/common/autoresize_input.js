/* @odoo-module */

import { onExternalClick } from "@mail/utils/common/hooks";

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
        value: { type: String },
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
        });
        this.inputRef = useRef("input");
        onWillUpdateProps((nextProps) => {
            if (this.props.value !== nextProps.value) {
                this.state.value = nextProps.value;
            }
        });
        onExternalClick("input", async (ev, { downTarget }) => {
            if (downTarget === this.inputRef.el) {
                return;
            }
            this.onValidate();
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
                this.onValidate();
                this.inputRef.el.blur();
                break;
            case "Escape":
                this.onDiscard();
                this.inputRef.el.blur();
                break;
        }
    }

    onValidate() {
        this.props.onValidate(this.state.value);
        this.state.value = this.props.value;
    }

    onDiscard() {
        this.state.value = this.props.value;
    }
}
