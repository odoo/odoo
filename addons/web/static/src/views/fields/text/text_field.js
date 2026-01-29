/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useAutoresize } from "@web/core/utils/autoresize";
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
        lineBreaks: { type: Boolean, optional: true },
        placeholder: { type: String, optional: true },
        dynamicPlaceholder: { type: Boolean, optional: true },
        dynamicPlaceholderModelReferenceField: { type: String, optional: true },
        rowCount: { type: Number, optional: true },
    };
    static defaultProps = {
        lineBreaks: true,
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
            preventLineBreaks: !this.props.lineBreaks,
        });
        useSpellCheck({ refName: "textarea" });

        useAutoresize(this.textareaRef, { minimumHeight: this.minimumHeight });
    }

    get isTranslatable() {
        return this.props.record.fields[this.props.name].translate;
    }
    get minimumHeight() {
        return this.props.lineBreaks ? 50 : 0;
    }
    get rowCount() {
        return this.props.lineBreaks ? this.props.rowCount : 1;
    }
}

export const textField = {
    component: TextField,
    displayName: _t("Multiline Text"),
    supportedOptions: [
        {
            label: _t("Enable line breaks"),
            name: "line_breaks",
            type: "boolean",
            default: true,
        },
    ],
    supportedTypes: ["html", "text"],
    extractProps: ({ attrs, options }) => ({
        placeholder: attrs.placeholder,
        dynamicPlaceholder: options?.dynamic_placeholder || false,
        dynamicPlaceholderModelReferenceField:
            options?.dynamic_placeholder_model_reference_field || "",
        rowCount: attrs.rows && parseInteger(attrs.rows),
        lineBreaks: options?.line_breaks !== undefined ? Boolean(options.line_breaks) : true,
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
