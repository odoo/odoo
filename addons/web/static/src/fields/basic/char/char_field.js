// @ts-check

/** @module @web/fields/basic/char/char_field - Single-line text input field for Char columns */

import { useEffect, useExternalListener, useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { exprToBoolean } from "@web/core/utils/format/strings";
import { useDynamicPlaceholder } from "@web/fields/dynamic_placeholder_hook";
import { formatChar } from "@web/fields/formatters";
import { useInputField } from "@web/fields/input_field_hook";
import { standardFieldProps } from "@web/fields/standard_field_props";
import { TranslationButton } from "@web/fields/translation_button";

import { TextInputFieldBase } from "../text_input_field_base";

export class CharField extends TextInputFieldBase {
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

    /** @returns {HTMLInputElement | null} */
    get inputEl() {
        return this.input.el;
    }

    setup() {
        this.input = useRef("input");
        if (this.props.dynamicPlaceholder) {
            this.dynamicPlaceholder = useDynamicPlaceholder(this.input);
            useExternalListener(document, "keydown", this.dynamicPlaceholder.onKeydown);
            useEffect(() =>
                this.dynamicPlaceholder.updateModel(
                    this.props.dynamicPlaceholderModelReferenceField,
                ),
            );
        }
        useInputField({
            getValue: () => this.props.record.data[this.props.name] || "",
            parse: (v) => this.parse(v),
        });

        this.selectionStart = this.props.record.data[this.props.name]?.length || 0;
    }

    /** @returns {boolean} Whether to trim whitespace (based on field `trim` attribute) */
    get shouldTrim() {
        return this.props.record.fields[this.props.name].trim && !this.props.isPassword;
    }
    /** @returns {number | undefined} Field size limit */
    get maxLength() {
        return this.props.record.fields[this.props.name].size;
    }
    /** @returns {string} Formatted display value (masked if password) */
    get formattedValue() {
        return formatChar(this.props.record.data[this.props.name], {
            isPassword: this.props.isPassword,
        });
    }
    /** @returns {boolean} */
    get hasDynamicPlaceholder() {
        return this.props.dynamicPlaceholder && !this.props.readonly;
    }

    /**
     * @param {string} value
     * @returns {string}
     */
    parse(value) {
        if (this.shouldTrim) {
            return value.trim();
        }
        return value;
    }

    onBlur() {
        this.selectionStart = /** @type {HTMLInputElement} */ (
            this.input.el
        ).selectionStart;
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
                "Displays the value of the selected field as a textual hint. If the selected field is empty, the static placeholder attribute is displayed instead.",
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
