import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useInputField } from "../input_field_hook";
import { useNumpadDecimal } from "../numpad_decimal_hook";
import { formatFloat } from "../formatters";
import { parseFloat } from "../parsers";
import { standardFieldProps } from "../standard_field_props";

import { Component, props, proxy, t } from "@odoo/owl";

export const floatFieldProps = {
    ...standardFieldProps,
    formatNumber: t.boolean().optional(true),
    inputType: t.string().optional("text"),
    step: t.number().optional(),
    digits: t.array().optional(),
    minDigits: t.number().optional(),
    humanReadable: t.boolean().optional(false),
    decimals: t.number().optional(0),
    trailingZeros: t.boolean().optional(true),
    externalPlaceholder: t.string().optional(),
};

export class FloatField extends Component {
    static template = "web.FloatField";
    props = props(floatFieldProps);

    setup() {
        this.state = proxy({
            hasFocus: false,
        });
        this.inputRef = useInputField({
            getValue: () => this.formattedValue,
            refName: "numpadDecimal",
            parse: (v) => this.parse(v),
        });
        useNumpadDecimal();
    }

    onFocusIn() {
        this.state.hasFocus = true;
    }

    onFocusOut() {
        this.state.hasFocus = false;
    }

    parse(value) {
        return this.props.inputType === "number"
            ? Number(value)
            : parseFloat(value, { allowOperation: true });
    }

    format(value) {
        const options = {
            digits: this.props.digits,
            minDigits: this.props.minDigits,
            field: this.props.record.fields[this.props.name],
            trailingZeros: this.props.trailingZeros,
        };
        if (this.props.humanReadable && !this.state.hasFocus) {
            return formatFloat(this.value, {
                ...options,
                humanReadable: true,
                decimals: this.props.decimals,
            });
        } else {
            return formatFloat(value, { ...options, humanReadable: false });
        }
    }

    get formattedValue() {
        if (!this.value && this.props.externalPlaceholder) {
            return "";
        }
        if (
            !this.props.formatNumber ||
            (this.props.inputType === "number" && !this.props.readonly && this.value)
        ) {
            return this.value;
        }
        return this.format(this.value);
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    get placeholderValue() {
        const externalPlaceholder = this.props.record.data[this.props.externalPlaceholder];
        if (externalPlaceholder === undefined) {
            return "...";
        }
        if (typeof externalPlaceholder === "number") {
            return this.format(externalPlaceholder);
        }
        return externalPlaceholder;
    }
}

export const floatField = {
    component: FloatField,
    displayName: _t("Float"),
    supportedOptions: [
        {
            label: _t("Format number"),
            name: "enable_formatting",
            type: "boolean",
            help: _t(
                "Format the value according to your language setup - e.g. thousand separators, rounding, etc."
            ),
            default: true,
        },
        {
            label: _t("Digits"),
            name: "digits",
            type: "digits",
        },
        {
            label: _t("Minimum Digits"),
            name: "minDigits",
            type: "digits",
        },
        {
            label: _t("Type"),
            name: "type",
            type: "string",
        },
        {
            label: _t("Step"),
            name: "step",
            type: "number",
        },
        {
            label: _t("User-friendly format"),
            name: "human_readable",
            type: "boolean",
            help: _t("Use a human readable format (e.g.: 500G instead of 500,000,000,000)."),
        },
        {
            label: _t("Hide trailing zeros"),
            name: "hide_trailing_zeros",
            type: "boolean",
            help: _t("Hide zeros to the right of the last non-zero digit, e.g. 1.20 becomes 1.2"),
        },
        {
            label: _t("Decimals"),
            name: "decimals",
            type: "number",
            default: 0,
            help: _t("Use it with the 'User-friendly format' option to customize the formatting."),
        },
        {
            label: _t("Placeholder field"),
            name: "placeholder_field",
            type: "field",
            availableTypes: ["float"],
        },
    ],
    supportedTypes: ["float", "monetary"],
    isEmpty: (record, fieldName) => record.data[fieldName] === false,
    extractProps: ({ attrs, options }) => {
        // Sadly, digits param was available as an option and an attr.
        // The option version could be removed with some xml refactoring.
        let digits;
        if (attrs.digits) {
            digits = JSON.parse(attrs.digits);
        } else if (options.digits) {
            digits = options.digits;
        }

        return {
            formatNumber:
                options?.enable_formatting !== undefined
                    ? Boolean(options.enable_formatting)
                    : true,
            inputType: options.type,
            humanReadable: !!options.human_readable,
            step: options.step,
            digits,
            minDigits: options.min_display_digits,
            decimals: options.decimals || 0,
            trailingZeros: !options.hide_trailing_zeros,
            externalPlaceholder: options.placeholder_field,
        };
    },
};

registry.category("fields").add("float", floatField);
