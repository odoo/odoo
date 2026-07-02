import { useLayoutEffect, useRef } from "@web/owl2/utils";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useAutoresize } from "@web/core/utils/autoresize";
import { useSpellCheck } from "@web/core/utils/hooks";
import { useDynamicPlaceholder } from "../dynamic_placeholder_hook";
import { useInputField } from "../input_field_hook";
import { parseInteger } from "../parsers";
import { standardFieldProps } from "../standard_field_props";
import { TranslationButton } from "../translation/translation";

import { Component, props, t, useListener } from "@odoo/owl";

export const textFieldProps = {
    ...standardFieldProps,
    lineBreaks: t.boolean().optional(true),
    placeholder: t.string().optional(),
    dynamicPlaceholder: t.boolean().optional(false),
    dynamicPlaceholderModelReferenceField: t.string().optional(),
    rowCount: t.number().optional(2),
};

export class TextField extends Component {
    static template = "web.TextField";
    static components = {
        TranslationButton,
    };
    props = props(textFieldProps);

    setup() {
        this.textareaRef = useRef("textarea");
        if (this.props.dynamicPlaceholder) {
            this.dynamicPlaceholder = useDynamicPlaceholder(this.textareaRef);
            useListener(document, "keydown", this.dynamicPlaceholder.onKeydown);
            useLayoutEffect(() =>
                this.dynamicPlaceholder.updateModel(
                    this.props.dynamicPlaceholderModelReferenceField
                )
            );
        }
        useInputField({
            getValue: () => this.props.record.data[this.props.name] || "",
            refName: "textarea",
            parse: (v) => this.parse(v),
            preventLineBreaks: !this.props.lineBreaks,
        });
        useSpellCheck({ refName: "textarea" });

        useAutoresize(this.textareaRef, { minimumHeight: this.minimumHeight });

        this.selectionStart = this.props.record.data[this.props.name]?.length || 0;
    }

    get shouldTrim() {
        return this.props.record.fields[this.props.name].trim;
    }

    parse(value) {
        if (this.shouldTrim) {
            return value.trim();
        }
        return value;
    }

    onBlur() {
        this.selectionStart = this.textareaRef.el?.selectionStart || 0;
    }

    async onDynamicPlaceholderOpen() {
        await this.dynamicPlaceholder.open({
            validateCallback: this.onDynamicPlaceholderValidate.bind(this),
        });
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

    async onDynamicPlaceholderValidate(chain, defaultValue) {
        if (chain) {
            this.textareaRef.el.focus();
            const dynamicPlaceholder = ` {{object.${chain}${
                defaultValue?.length ? ` ||| ${defaultValue}` : ""
            }}}`;
            this.textareaRef.el.setRangeText(
                dynamicPlaceholder,
                this.selectionStart,
                this.selectionStart,
                "end"
            );
            // trigger events to make the field dirty
            this.textareaRef.el.dispatchEvent(new InputEvent("input"));
            this.textareaRef.el.dispatchEvent(new KeyboardEvent("keydown"));
            this.textareaRef.el.focus();
        }
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
        {
            label: _t("Dynamic Placeholder"),
            name: "placeholder_field",
            type: "field",
            availableTypes: ["char"],
        },
    ],
    supportedTypes: ["html", "text", "char"],
    extractProps: ({ attrs, options, placeholder }) => ({
        placeholder,
        dynamicPlaceholder: options?.dynamic_placeholder || false,
        dynamicPlaceholderModelReferenceField:
            options?.dynamic_placeholder_model_reference_field || "",
        rowCount: attrs.rows && parseInteger(attrs.rows),
        lineBreaks: options?.line_breaks !== undefined ? Boolean(options.line_breaks) : true,
    }),
};

registry.category("fields").add("text", textField);

export class ListTextField extends TextField {
    props = props({
        ...textFieldProps,
        rowCount: t.number().optional(1),
    });

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
