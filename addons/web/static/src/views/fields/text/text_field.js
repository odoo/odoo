/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useSpellCheck } from "@web/core/utils/hooks";
import { useDynamicPlaceholder } from "../dynamic_placeholder_hook";
import { useInputField } from "../input_field_hook";
import { parseInteger } from "../parsers";
import { standardFieldProps } from "../standard_field_props";
import { TranslationButton } from "../translation_button";

import { Component, useExternalListener, useEffect, useRef } from "@odoo/owl";

export class TextField extends Component {
    static template = "web.TextField";
    static components = {
        TranslationButton,
    };
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
        dynamicPlaceholder: { type: Boolean, optional: true },
        dynamicPlaceholderModelReferenceField: { type: String, optional: true },
        rowCount: { type: Number, optional: true },
    };
    static defaultProps = {
        dynamicPlaceholder: false,
        rowCount: 2,
    };

    setup() {
        this.divRef = useRef("div");
        this.textareaRef = useRef("textarea");
        if (this.props.dynamicPlaceholder) {
            const dynamicPlaceholder = useDynamicPlaceholder(this.textareaRef);
            useExternalListener(document, "keydown", dynamicPlaceholder.onKeydown);
            useEffect(() =>
                dynamicPlaceholder.updateModel(this.props.dynamicPlaceholderModelReferenceField)
            );
        }
        useInputField({
            getValue: () => this.props.record.data[this.props.name] || "",
            refName: "textarea",
        });
        useSpellCheck({ refName: "textarea" });

        useEffect(() => {
            if (!this.props.readonly) {
                this.resize();
            }
        });
    }

    get isTranslatable() {
        return this.props.record.fields[this.props.name].translate;
    }
    get minimumHeight() {
        return 50;
    }
    get rowCount() {
        return this.props.rowCount;
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
        const previousStyle = {
            borderTopWidth: style.borderTopWidth,
            borderBottomWidth: style.borderBottomWidth,
            padding: style.padding,
        };
        Object.assign(textarea.style, {
            height: "auto",
            borderTopWidth: 0,
            borderBottomWidth: 0,
            padding: 0,
        });
        textarea.style.height = "auto";
        const height = Math.max(this.minimumHeight, textarea.scrollHeight + heightOffset);
        Object.assign(textarea.style, previousStyle, { height: `${height}px` });
        this.divRef.el.style.height = `${height}px`;
    }

    onInput() {
        this.resize();
    }
}

export const textField = {
    component: TextField,
    displayName: _lt("Multiline Text"),
    supportedTypes: ["html", "text"],
    extractProps: ({ attrs, options }) => ({
        placeholder: attrs.placeholder,
        dynamicPlaceholder: options?.dynamic_placeholder || false,
        dynamicPlaceholderModelReferenceField: options?.dynamic_placeholder_model_reference_field || "",
        rowCount: attrs.rows && parseInteger(attrs.rows),
    }),
};

registry.category("fields").add("text", textField);

export class ListTextField extends TextField {
    static defaultProps = {
        ...super.defaultProps,
        rowCount: 1,
    };

    get minimumHeight() {
        return 0;
    }
    get rowCount() {
        return this.props.rowCount;
    }
}

export const listTextField = {
    ...textField,
    component: ListTextField,
};

registry.category("fields").add("list.text", listTextField);
