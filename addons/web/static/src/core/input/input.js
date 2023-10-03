/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useInputHook } from "./input_hook";

export class Input extends Component {
    static template = "web.Input";
    static props = {
        id: {
            type: true,
            optional: true,
        },
        value: {
            type: String,
            optional: true,
        },
        onChange: Function,
        className: {
            type: String,
            optional: true,
        },
    };

    setup() {
        useInputHook({
            getValue: () => this.props.value || "",
            onChange: this.props.onChange,
        });
    }
}
