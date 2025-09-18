// @ts-check

/** @module @web/fields/basic/text/text_field - Multi-line textarea input field for Text columns */

import { useEffect, useExternalListener, useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useAutoresize } from "@web/core/utils/dom/autoresize";
import { useSpellCheck } from "@web/core/utils/hooks";
import { useDynamicPlaceholder } from "@web/fields/dynamic_placeholder_hook";
import { useInputField } from "@web/fields/input_field_hook";
import { parseInteger } from "@web/fields/parsers";
import { standardFieldProps } from "@web/fields/standard_field_props";
import { TranslationButton } from "@web/fields/translation_button";

import { TextInputFieldBase } from "../text_input_field_base";

export class TextField extends TextInputFieldBase {
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

    /** @returns {HTMLTextAreaElement | null} */
    get inputEl() {
        return this.textareaRef.el;
    }

    setup() {
        this.divRef = useRef("div");
        this.textareaRef = useRef("textarea");
        if (this.props.dynamicPlaceholder) {
            this.dynamicPlaceholder = useDynamicPlaceholder(this.textareaRef);
            useExternalListener(document, "keydown", this.dynamicPlaceholder.onKeydown);
            useEffect(() =>
                this.dynamicPlaceholder.updateModel(
                    this.props.dynamicPlaceholderModelReferenceField,
                ),
            );
        }
        useInputField({
            getValue: () => this.props.record.data[this.props.name] || "",
            refName: "textarea",
            parse: (v) => this.parse(v),
            preventLineBreaks: !this.props.lineBreaks,
        });
        useSpellCheck({ refName: "textarea" });

        useAutoresize(/** @type {any} */ (this.textareaRef), {
            minimumHeight: this.minimumHeight,
        });

        this.selectionStart = this.props.record.data[this.props.name]?.length || 0;
    }

    /** @returns {boolean} */
    get shouldTrim() {
        return this.props.record.fields[this.props.name].trim;
    }

    /** @param {string} value @returns {string} */
    parse(value) {
        if (this.shouldTrim) {
            return value.trim();
        }
        return value;
    }

    /** @returns {Promise<void>} */
    async onBlur() {
        this.selectionStart = /** @type {HTMLTextAreaElement} */ (
            this.textareaRef.el
        ).selectionStart;
    }

    /** @returns {number} */
    get minimumHeight() {
        return this.props.lineBreaks ? 50 : 0;
    }
    /** @returns {number} */
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
        lineBreaks:
            options?.line_breaks !== undefined ? Boolean(options.line_breaks) : true,
    }),
};

registry.category("fields").add("text", textField);

export class ListTextField extends TextField {
    static defaultProps = {
        ...super.defaultProps,
        rowCount: 1,
    };

    // @ts-ignore — narrower return type is intentional for list view
    /** @returns {number} */
    get minimumHeight() {
        return 0;
    }
    /** @returns {number} */
    get rowCount() {
        return this.props.rowCount;
    }
}

export const listTextField = {
    ...textField,
    component: ListTextField,
};

registry.category("fields").add("list.text", listTextField);
