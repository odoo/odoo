/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { archParseBoolean } from "@web/views/utils";
import { formatChar } from "../formatters";
import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";
import { TranslationButton } from "../translation_button";
import { useDynamicPlaceholder } from "../dynamicplaceholder_hook";

import { Component, onMounted, onWillUnmount, useRef } from "@odoo/owl";

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
        shouldTrim: { type: Boolean, optional: true },
        maxLength: { type: Number, optional: true },
        isTranslatable: { type: Boolean, optional: true },
    };
    static defaultProps = { dynamicPlaceholder: false };

    setup() {
        if (this.props.dynamicPlaceholder) {
            this.dynamicPlaceholder = useDynamicPlaceholder();
        }

        this.input = useRef("input");
        useInputField({ getValue: () => this.props.value || "", parse: (v) => this.parse(v) });
        onMounted(this.onMounted);
        onWillUnmount(this.onWillUnmount);
    }
    async onKeydownListener(ev) {
        if (ev.key === this.dynamicPlaceholder.TRIGGER_KEY && ev.target === this.input.el) {
            const baseModel = this.props.record.data.mailing_model_real;
            if (baseModel) {
                await this.dynamicPlaceholder.open(this.input.el, baseModel, {
                    validateCallback: this.onDynamicPlaceholderValidate.bind(this),
                    closeCallback: this.onDynamicPlaceholderClose.bind(this),
                });
            }
        }
    }
    onMounted() {
        if (this.props.dynamicPlaceholder) {
            this.keydownListenerCallback = this.onKeydownListener.bind(this);
            document.addEventListener("keydown", this.keydownListenerCallback);
        }
    }
    onWillUnmount() {
        if (this.props.dynamicPlaceholder) {
            document.removeEventListener("keydown", this.keydownListenerCallback);
        }
    }
    onDynamicPlaceholderValidate(chain, defaultValue) {
        if (chain) {
            const triggerKeyReplaceRegex = new RegExp(`${this.dynamicPlaceholder.TRIGGER_KEY}$`);
            let dynamicPlaceholder = "{{object." + chain.join(".");
            dynamicPlaceholder +=
                defaultValue && defaultValue !== "" ? ` or '''${defaultValue}'''}}` : "}}";
            this.props.record.update({
                [this.props.name]:
                    this.input.el.value.replace(triggerKeyReplaceRegex, "") + dynamicPlaceholder,
            });
        }
    }
    onDynamicPlaceholderClose() {
        this.input.el.focus();
    }

    get formattedValue() {
        return formatChar(this.props.value, { isPassword: this.props.isPassword });
    }

    parse(value) {
        if (this.props.shouldTrim) {
            return value.trim();
        }
        return value;
    }
}

export const charField = {
    component: CharField,
    displayName: _lt("Text"),
    supportedTypes: ["char"],
    extractProps: ({ attrs, field }) => ({
        isPassword: archParseBoolean(attrs.password),
        dynamicPlaceholder: attrs.options.dynamic_placeholder,
        autocomplete: attrs.autocomplete,
        placeholder: attrs.placeholder,

        shouldTrim: field.trim && !archParseBoolean(attrs.password), // passwords shouldn't be trimmed
        maxLength: field.size,
        isTranslatable: field.translate,
    }),
};

registry.category("fields").add("char", charField);
