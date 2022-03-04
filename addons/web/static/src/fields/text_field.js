/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";
import { TranslationButton } from "./translation_button";

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

    get isTranslatable() {
        return this.props.record.fields[this.props.name].translate;
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
        this.props.update(ev.target.value);
    }
}

TextField.template = "web.TextField";
TextField.props = {
    ...standardFieldProps,
    placeholder: { type: String, optional: true },
};
TextField.components = {
    TranslationButton,
};
TextField.displayName = _lt("Multiline Text");
TextField.supportedTypes = ["html", "text"];

registry.category("fields").add("text", TextField);
registry.category("fields").add("list.text", TextField);
registry.category("fields").add("html", TextField);
