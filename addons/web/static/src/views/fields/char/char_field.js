import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { exprToBoolean } from "@web/core/utils/strings";
import { useDynamicPlaceholder } from "../dynamic_placeholder_hook";
import { formatChar } from "../formatters";
import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";
import { TranslationButton } from "../translation_button";

import { Component, useEffect, useExternalListener, useRef } from "@odoo/owl";

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
        placeholderField: { type: String, optional: true },
    };
    static defaultProps = { dynamicPlaceholder: false };

    setup() {
        this.input = useRef("input");
        if (this.props.dynamicPlaceholder) {
            this.dynamicPlaceholder = useDynamicPlaceholder(this.input);
            useExternalListener(document, "keydown", this.dynamicPlaceholder.onKeydown);
            useEffect(() =>
                this.dynamicPlaceholder.updateModel(
                    this.props.dynamicPlaceholderModelReferenceField
                )
            );
        }
        useInputField({
            getValue: () => this.props.record.data[this.props.name] || "",
            parse: (v) => this.parse(v),
        });

        this.selectionStart = this.props.record.data[this.props.name]?.length || 0;
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
    get hasDynamicPlaceholder() {
        return this.props.dynamicPlaceholder && !this.props.readonly;
    }

    get placeholder() {
        return this.props.record.data[this.props.placeholderField] || this.props.placeholder;
    }

    parse(value) {
        if (this.shouldTrim) {
            return value.trim();
        }
        return value;
    }

    onBlur() {
        this.selectionStart = this.input.el.selectionStart;
    }

    async onDynamicPlaceholderOpen() {
        await this.dynamicPlaceholder.open({
            validateCallback: this.onDynamicPlaceholderValidate.bind(this),
        });
    }

    async onDynamicPlaceholderValidate(chain, defaultValue) {
        if (chain) {
            this.input.el.focus();
            const dynamicPlaceholder = ` {{object.${chain}${
                defaultValue?.length ? ` ||| ${defaultValue}` : ""
            }}}`;
            this.input.el.setRangeText(
                dynamicPlaceholder,
                this.selectionStart,
                this.selectionStart,
                "end"
            );
            // trigger events to make the field dirty
            this.input.el.dispatchEvent(new InputEvent("input"));
            this.input.el.dispatchEvent(new KeyboardEvent("keydown"));
            this.input.el.focus();
        }
    }
}

export const charField = {
    component: CharField,
    displayName: _t("Text"),
    supportedTypes: ["char"],
    supportedOptions: [
        {
            label: _t("Dynamic Placeholder"),
            name: "placeholder_field",
            type: "field",
            availableTypes: ["char"],
            help: _t(
                "Displays the value of the selected field as a textual hint. If the selected field is empty, the static placeholder attribute is displayed instead."
            ),
        },
    ],
    extractProps: ({ attrs, options }) => ({
        isPassword: exprToBoolean(attrs.password),
        dynamicPlaceholder: options.dynamic_placeholder || false,
        dynamicPlaceholderModelReferenceField:
            options.dynamic_placeholder_model_reference_field || "",
        autocomplete: attrs.autocomplete,
        placeholder: attrs.placeholder,
        placeholderField: options.placeholder_field,
    }),
};

registry.category("fields").add("char", charField);
