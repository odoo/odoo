/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

const { Component, useEffect, useRef } = owl;

export class TextField extends Component {
    setup() {
        this.textareaRef = useRef("textarea");

        useEffect(() => {
            if (!this.props.readonly) {
                this.resize();
            }
        });
    }

    resize() {
        const textarea = this.textareaRef.el;
        let heightOffset = 0;
        const style = window.getComputedStyle(textarea);
        if (style.boxSizing === "border-box") {
            const paddingHeight = parseFloat(style.paddingTop) + parseFloat(style.paddingBottom);
            const borderHeight =
                parseFloat(style.borderTopWidth) + parseFloat(style.borderBottomWidth);
            heightOffset = borderHeight + paddingHeight;
        }
        textarea.style.height = "auto";
        textarea.style.height = `${textarea.scrollHeight + heightOffset}px`;
    }

    onInput() {
        this.resize();
    }
    onChange(ev) {
        this.props.record.update(this.props.name, ev.target.value);
    }
}

TextField.template = "web.TextField";
TextField.props = {
    ...standardFieldProps,
    placeholder: { type: String, optional: true },
};
TextField.displayName = _lt("Multiline Text");
TextField.supportedTypes = ["html", "text"];

registry.category("fields").add("text", TextField);
registry.category("fields").add("html", TextField);
