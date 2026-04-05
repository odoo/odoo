/** @odoo-module **/

import { Component } from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";

export class Input extends Component {
    static template = "odx_owl.Input";
    static props = {
        attrs: { type: Object, optional: true },
        ariaLabel: { type: String, optional: true },
        autocomplete: { type: String, optional: true },
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        id: { type: String, optional: true },
        name: { type: String, optional: true },
        onChange: { type: Function, optional: true },
        onInput: { type: Function, optional: true },
        placeholder: { type: String, optional: true },
        readonly: { type: Boolean, optional: true },
        required: { type: Boolean, optional: true },
        type: { type: String, optional: true },
        value: { optional: true, validate: () => true },
    };
    static defaultProps = {
        attrs: {},
        className: "",
        disabled: false,
        readonly: false,
        required: false,
        type: "text",
        value: "",
    };

    get classes() {
        return cn("odx-input", this.props.className);
    }

    onInput(ev) {
        this.props.onInput?.(ev.target.value, ev);
    }

    onChange(ev) {
        this.props.onChange?.(ev.target.value, ev);
    }
}
