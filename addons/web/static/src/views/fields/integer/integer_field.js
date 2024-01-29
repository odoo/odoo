import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatInteger } from "../formatters";
import { parseInteger } from "../parsers";
import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";
import { useNumpadDecimal } from "../numpad_decimal_hook";

import { Component, useState } from "@odoo/owl";

export class IntegerField extends Component {
    static template = "web.IntegerField";
    static props = {
        ...standardFieldProps,
        formatNumber: { type: Boolean, optional: true },
        humanReadable: { type: Boolean, optional: true },
        decimals: { type: Number, optional: true },
        inputType: { type: String, optional: true },
        step: { type: Number, optional: true },
        placeholder: { type: String, optional: true },
    };
    static defaultProps = {
        formatNumber: true,
        humanReadable: false,
        inputType: "text",
        decimals: 0,
    };

    setup() {
        this.state = useState({
            hasFocus: false,
        });
        useInputField({
            getValue: () => this.formattedValue,
            refName: "numpadDecimal",
            parse: (v) => parseInteger(v),
        });
        useNumpadDecimal();
    }

    onFocusIn() {
        this.state.hasFocus = true;
    }

    onFocusOut() {
        this.state.hasFocus = false;
    }

    get formattedValue() {
        if (
            !this.props.formatNumber ||
            (!this.props.readonly && this.props.inputType === "number")
        ) {
            return this.value;
        }
        if (this.props.humanReadable && !this.state.hasFocus) {
            return formatInteger(this.value, {
                humanReadable: true,
                decimals: this.props.decimals,
            });
        } else {
            return formatInteger(this.value, { humanReadable: false });
        }
    }

    get value() {
        return this.props.record.data[this.props.name];
    }
}

export const integerField = {
    component: IntegerField,
    displayName: _t("Integer"),
    supportedOptions: [
        {
            label: _t("Format number"),
            name: "enable_formatting",
            type: "boolean",
            help: _t(
                "Format the value according to your language setup - e.g. thousand separators, rounding, etc."
            ),
            default: true,
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
            label: _t("Decimals"),
            name: "decimals",
            type: "number",
            default: 0,
            help: _t("Use it with the 'User-friendly format' option to customize the formatting."),
        },
    ],
    supportedTypes: ["integer"],
    isEmpty: (record, fieldName) => record.data[fieldName] === false,
    extractProps: ({ attrs, options }) => ({
        formatNumber:
            options?.enable_formatting !== undefined ? Boolean(options.enable_formatting) : true,
        humanReadable: !!options.human_readable,
        inputType: options.type,
        step: options.step,
        placeholder: attrs.placeholder,
        decimals: options.decimals || 0,
    }),
};

registry.category("fields").add("integer", integerField);
