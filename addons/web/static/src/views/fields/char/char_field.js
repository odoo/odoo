/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { archParseBoolean } from "@web/views/utils";
import { formatChar } from "../formatters";
import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";
import { TranslationButton } from "../translation_button";
import { useDynamicPlaceholder } from "../dynamic_placeholder_hook";

import { Component, useExternalListener, useRef, useEffect } from "@odoo/owl";

export class CharField extends Component {
    static template = "web.CharField";
    static components = {
        TranslationButton,
    };
    static props = {
        ...standardFieldProps,
        autocomplete: { type: String, optional: true },
        isPassword: { type: Boolean, optional: true },
        placeholder: { type: String, optional: true },
        dynamicPlaceholder: { type: Boolean, optional: true },
        dynamicPlaceholderModelReferenceField: { type: String, optional: true },
    };
    static defaultProps = { dynamicPlaceholder: false };

    setup() {
        this.input = useRef("input");
        if (this.props.dynamicPlaceholder) {
            const dynamicPlaceholder = useDynamicPlaceholder(this.input);
            useExternalListener(document, "keydown", dynamicPlaceholder.onKeydown);
            useEffect(() =>
                dynamicPlaceholder.updateModel(this.props.dynamicPlaceholderModelReferenceField)
            );
        }
        useInputField({
            getValue: () => this.props.record.data[this.props.name] || "",
            parse: (v) => this.parse(v),
        });
    }

    get shouldTrim() {
        return this.props.record.fields[this.props.name].trim && !this.props.isPassword;
    }
    get maxLength() {
        return this.props.record.fields[this.props.name].size;
    }
    get isTranslatable() {
        return this.props.record.fields[this.props.name].translate;
    }
    get formattedValue() {
        return formatChar(this.props.record.data[this.props.name], {
            isPassword: this.props.isPassword,
        });
    }

    parse(value) {
        if (this.shouldTrim) {
            return value.trim();
        }
        return value;
    }
}

export const charField = {
    component: CharField,
    displayName: _t("Text"),
    supportedTypes: ["char"],
    supportedOptions: [
        {
            label: _t("Dynamic placeholder"),
            name: "dynamic_placeholder",
            type: "boolean",
            help: _t("Enable this option to allow the input to display a dynamic placeholder."),
        },
        {
            label: _t("Model reference field"),
            name: "dynamic_placeholder_model_reference_field",
            type: "field",
            supportedTypes: ["char"],
        },
    ],
    extractProps: ({ attrs, options }) => ({
        isPassword: archParseBoolean(attrs.password),
        dynamicPlaceholder: options.dynamic_placeholder || false,
        dynamicPlaceholderModelReferenceField:
            options.dynamic_placeholder_model_reference_field || "",
        autocomplete: attrs.autocomplete,
        placeholder: attrs.placeholder,
    }),
};

registry.category("fields").add("char", charField);
