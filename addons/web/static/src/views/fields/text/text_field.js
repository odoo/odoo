/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";
import { TranslationButton } from "../translation_button";

const { Component, useEffect, useRef } = owl;

export class TextField extends Component {
    setup() {
        this.textareaRef = useRef("textarea");
        useInputField({ getValue: () => this.props.value || "", refName: "textarea" });

        useEffect(() => {
            if (!this.props.readonly) {
                this.resize();
            }
        });
    }

    get minimumHeight() {
        return 50;
    }
    get rowCount() {
        return 2;
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
        Object.assign(textarea.style, {
            height: "auto",
            borderTopWidth: 0,
            borderBottomWidth: 0,
            padding: 0,
        });
        textarea.style.height = "auto";
        const height = Math.max(this.minimumHeight, textarea.scrollHeight + heightOffset);
        Object.assign(textarea.style, {
            height: `${height}px`,
            borderTopWidth: style.borderTopWidth,
            borderBottomWidth: style.borderBottomWidth,
            padding: style.padding,
        });
    }

    onInput() {
        this.resize();
    }
}

TextField.template = "web.TextField";
TextField.components = {
    TranslationButton,
};
TextField.props = {
    ...standardFieldProps,
    isTranslatable: { type: Boolean, optional: true },
    resId: { type: [Number, Boolean], optional: true },
    resModel: { type: String, optional: true },
};

TextField.displayName = _lt("Multiline Text");
TextField.supportedTypes = ["html", "text"];

TextField.extractProps = (fieldName, record, attrs) => {
    return {
        isTranslatable: record.fields[fieldName].translate,
        placeholder: attrs.placeholder,
        resId: record.resId,
        resModel: record.resModel,
    };
};

registry.category("fields").add("text", TextField);

class ListTextField extends TextField {
    get minimumHeight() {
        return 0;
    }
    get rowCount() {
        return 1;
    }
}

ListTextField.template = "web.TextField";
ListTextField.components = {
    TranslationButton,
};
ListTextField.props = {
    ...standardFieldProps,
    isTranslatable: { type: Boolean, optional: true },
    resId: { type: [Number, Boolean], optional: true },
    resModel: { type: String, optional: true },
};

ListTextField.displayName = _lt("Multiline Text");
ListTextField.supportedTypes = ["html", "text"];

ListTextField.extractProps = (fieldName, record, attrs) => {
    return {
        isTranslatable: record.fields[fieldName].translate,
        placeholder: attrs.placeholder,
        resId: record.resId,
        resModel: record.resModel,
    };
};

registry.category("fields").add("list.text", ListTextField);
