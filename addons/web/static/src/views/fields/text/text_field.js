import { useExternalListener, useLayoutEffect } from "@web/owl2/utils";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useAutoresize } from "@web/core/utils/autoresize";
import { useSpellCheck } from "@web/core/utils/hooks";
import { useDynamicPlaceholder } from "../dynamic_placeholder_hook";
import { useInputField } from "../input_field_hook";
import { parseInteger } from "../parsers";
import { standardFieldProps } from "../standard_field_props";
import { TranslationButton } from "../translation_button";

import { Component, signal } from "@odoo/owl";

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

    textareaRef = signal(null);

    setup() {
        if (this.props.dynamicPlaceholder) {
            this.dynamicPlaceholder = useDynamicPlaceholder(this.textareaRef);
            useExternalListener(document, "keydown", this.dynamicPlaceholder.onKeydown);
            useLayoutEffect(() =>
                this.dynamicPlaceholder.updateModel(
                    this.props.dynamicPlaceholderModelReferenceField
                )
            );
        }
        useInputField({
            getValue: () => this.props.record.data[this.props.name] || "",
            ref: this.textareaRef,
            parse: (v) => this.parse(v),
            preventLineBreaks: !this.props.lineBreaks,
        });
        useSpellCheck({ ref: this.textareaRef });

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
        this.selectionStart = this.textareaRef()?.selectionStart || 0;
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
            const textarea = this.textareaRef();
            if (!textarea) {
                return;
            }
            textarea.focus();
            const dynamicPlaceholder = ` {{object.${chain}${
                defaultValue?.length ? ` ||| ${defaultValue}` : ""
            }}}`;
            textarea.setRangeText(
                dynamicPlaceholder,
                this.selectionStart,
                this.selectionStart,
                "end"
            );
            // trigger events to make the field dirty
            textarea.dispatchEvent(new InputEvent("input"));
            textarea.dispatchEvent(new KeyboardEvent("keydown"));
            textarea.focus();
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
