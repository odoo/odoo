/* @odoo-module */

import { onExternalClick } from "@mail/utils/hooks";
import { Component, useRef, useState, onWillUpdateProps } from "@odoo/owl";
import { useAutoresize } from "@web/core/utils/autoresize";

export class AutoresizeInput extends Component {
    static template = "mail.AutoresizeInput";
    static props = {
        className: { type: String, optional: true },
        enabled: { optional: true },
        onValidate: { type: Function, optional: true },
        placeholder: { type: String, optional: true },
        value: { type: String },
    };
    static defaultProps = {
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
        onExternalClick("input", () => this.onValidate());
        useAutoresize(this.inputRef);
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
        if (this.state.value !== this.props.value) {
            this.props.onValidate({
                value: this.state.value,
            });
        }
        this.state.value = this.props.value;
    }

    onDiscard() {
        this.state.value = this.props.value;
    }
}
