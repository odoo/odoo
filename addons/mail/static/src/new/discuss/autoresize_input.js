/* @odoo-module */

import { onExternalClick } from "@mail/new/utils/hooks";
import { Component, useRef, useState, onWillUpdateProps, useEffect } from "@odoo/owl";

export class AutoresizeInput extends Component {
    static template = "mail.AutoresizeInput";
    static props = {
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        onValidate: { type: Function, optional: true },
        placeholder: { type: String, optional: true },
        value: { type: String },
    };
    static defaultProps = {
        className: "",
        onValidate: () => {},
        placeholder: "",
    };

    setup() {
        this.state = useState({
            value: this.props.value,
        });
        this.inputRef = useRef("input");
        this.maxWidth = undefined;
        onWillUpdateProps((nextProps) => {
            if (this.props.value !== nextProps.value) {
                this.state.value = nextProps.value;
            }
        });
        onExternalClick("input", () => this.onValidate());
        useEffect(
            () => {
                // This mesures the maximum width of the input which can get from the flex layout.
                this.inputRef.el.style.width = "100%";
                this.maxWidth = this.inputRef.el.clientWidth;
                // Minimum width of the input
                this.inputRef.el.style.width = "10px";
                if (this.state.value === "" && this.props.placeholder !== "") {
                    this.inputRef.el.style.width = "auto";
                    return;
                }
                if (this.inputRef.el.scrollWidth + 5 > this.maxWidth) {
                    this.inputRef.el.style.width = "100%";
                    return;
                }
                this.inputRef.el.style.width = this.inputRef.el.scrollWidth + 5 + "px";
            },
            () => [this.state.value]
        );
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
