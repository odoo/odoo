/** @odoo-module **/

import { Component, useRef } from "@odoo/owl";

import { useAutoresize } from "@web/core/utils/autoresize";
import { useInputHook } from "../input/input_hook";

export class Textarea extends Component {
    static template = "web.Textarea";
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
        this.textareaRef = useRef("input");
        useAutoresize(this.textareaRef, { minimumHeight: 50 });
        useInputHook({
            getValue: () => this.props.value || "",
            onChange: this.props.onChange,
        });
    }
}
