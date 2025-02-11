/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "../formatters";
import { parseMonetary } from "../parsers";
import { useInputField } from "../input_field_hook";
import { useNumpadDecimal } from "../numpad_decimal_hook";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";
import { getCurrency } from "@web/core/currency";

export class MonetaryField extends Component {
    static template = "web.MonetaryField";
    static props = {
        ...standardFieldProps,
        currencyField: { type: String, optional: true },
        inputType: { type: String, optional: true },
        useFieldDigits: { type: Boolean, optional: true },
        hideSymbol: { type: Boolean, optional: true },
        placeholder: { type: String, optional: true },
    };
    static defaultProps = {
        hideSymbol: false,
        inputType: "text",
    };

    setup() {
        useInputField(this.inputOptions);
        useNumpadDecimal();
    }

    get inputOptions() {
        return {
            getValue: () => this.formattedValue,
            refName: "numpadDecimal",
            parse: parseMonetary,
        };
    }

    get currencyId() {
        const currencyField =
            this.props.currencyField ||
            this.props.record.fields[this.props.name].currency_field ||
            "currency_id";
        const currency = this.props.record.data[currencyField];
        return currency && currency[0];
    }
    get currency() {
        if (!isNaN(this.currencyId)) {
            return getCurrency(this.currencyId) || null;
        }
        return null;
    }

    get currencySymbol() {
        return this.currency ? this.currency.symbol : "";
    }

    get currencyDigits() {
        if (this.props.useFieldDigits) {
            return this.props.record.fields[this.props.name].digits;
        }
        if (!this.currency) {
            return null;
        }
        return getCurrency(this.currencyId).digits;
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    get formattedValue() {
        if (this.props.inputType === "number" && !this.props.readonly && this.value) {
            return this.value;
        }
        return formatMonetary(this.value, {
            digits: this.currencyDigits,
            currencyId: this.currencyId,
            noSymbol: !this.props.readonly || this.props.hideSymbol,
        });
    }
}

export const monetaryField = {
    component: MonetaryField,
    supportedOptions: [
        {
            label: _t("Hide symbol"),
            name: "no_symbol",
            type: "boolean",
        },
        {
            label: _t("Currency"),
            name: "currency_field",
            type: "field",
            availableTypes: ["many2one"],
        },
    ],
    supportedTypes: ["monetary", "float"],
    displayName: _t("Monetary"),
    extractProps: ({ attrs, options }) => ({
        currencyField: options.currency_field,
        inputType: attrs.type,
        useFieldDigits: options.field_digits,
        hideSymbol: options.no_symbol,
        placeholder: attrs.placeholder,
    }),
};

registry.category("fields").add("monetary", monetaryField);
