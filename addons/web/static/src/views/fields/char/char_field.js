import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { exprToBoolean } from "@web/core/utils/strings";
import { useDynamicPlaceholder } from "../dynamic_placeholder_hook";
import { formatChar } from "../formatters";
import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";
import { TranslationButton } from "../translation_button";

import { Component, onMounted, onPatched, props, signal, t, useListener } from "@odoo/owl";

export const charFieldProps = {
    ...standardFieldProps,
    autocomplete: t.string().optional(),
    isPassword: t.boolean().optional(),
    placeholder: t.string().optional(),
    dynamicPlaceholder: t.boolean().optional(false),
    dynamicPlaceholderModelReferenceField: t.string().optional(),
};

export class CharField extends Component {
    static template = "web.CharField";
    static components = {
        TranslationButton,
    };
    props = props(charFieldProps);
    input = signal(null);

    setup() {
        if (this.props.dynamicPlaceholder) {
            this.dynamicPlaceholder = useDynamicPlaceholder(this.input);
            useListener(document, "keydown", this.dynamicPlaceholder.onKeydown);
            const updateModel = () =>
                this.dynamicPlaceholder.updateModel(
                    this.props.dynamicPlaceholderModelReferenceField
                );
            onMounted(updateModel);
            onPatched(updateModel);
        }
        useInputField({
            ref: this.input,
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

    parse(value) {
        if (this.shouldTrim) {
            return value.trim();
        }
        return value;
    }

    onBlur() {
        if (this.input()) {
            this.selectionStart = this.input().selectionStart;
        }
    }

    async onDynamicPlaceholderOpen() {
        await this.dynamicPlaceholder.open({
            validateCallback: this.onDynamicPlaceholderValidate.bind(this),
        });
    }

    async onDynamicPlaceholderValidate(chain, defaultValue) {
        if (chain) {
            this.input().focus();
            const dynamicPlaceholder = ` {{object.${chain}${
                defaultValue?.length ? ` ||| ${defaultValue}` : ""
            }}}`;
            this.input().setRangeText(
                dynamicPlaceholder,
                this.selectionStart,
                this.selectionStart,
                "end"
            );
            // trigger events to make the field dirty
            this.input().dispatchEvent(new InputEvent("input"));
            this.input().dispatchEvent(new KeyboardEvent("keydown"));
            this.input().focus();
        }
    }
}

export const charField = {
    component: CharField,
    displayName: _t("Text"),
    supportedTypes: ["char", "text"],
    supportedOptions: [
        {
            label: _t("Dynamic Placeholder"),
            name: "placeholder_field",
            type: "field",
            availableTypes: ["char", "text"],
            help: _t(
                "Displays the value of the selected field as a textual hint. If the selected field is empty, the static placeholder attribute is displayed instead."
            ),
        },
    ],
    extractProps: ({ attrs, options, placeholder }) => ({
        isPassword: exprToBoolean(attrs.password),
        dynamicPlaceholder: options.dynamic_placeholder || false,
        dynamicPlaceholderModelReferenceField:
            options.dynamic_placeholder_model_reference_field || "",
        autocomplete: attrs.autocomplete,
        placeholder,
    }),
};

registry.category("fields").add("char", charField);
