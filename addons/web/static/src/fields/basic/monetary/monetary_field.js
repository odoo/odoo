// @ts-check

/** @module @web/fields/basic/monetary/monetary_field - Currency-aware numeric input field for Monetary columns */

import { Component, useEffect, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { nbsp } from "@web/core/utils/format/strings";
import { formatMonetary } from "@web/fields/formatters";
import { useInputField } from "@web/fields/input_field_hook";
import { useNumpadDecimal } from "@web/fields/numpad_decimal_hook";
import { parseMonetary } from "@web/fields/parsers";
import { standardFieldProps } from "@web/fields/standard_field_props";
import { getCurrency } from "@web/services/currency";

export class MonetaryField extends Component {
    static template = "web.MonetaryField";
    static props = {
        ...standardFieldProps,
        currencyField: { type: String, optional: true },
        inputType: { type: String, optional: true },
        useFieldDigits: { type: Boolean, optional: true },
        hideSymbol: { type: Boolean, optional: true },
        trailingZeros: { type: Boolean, optional: true },
    };
    static defaultProps = {
        hideSymbol: false,
        inputType: "text",
        trailingZeros: true,
    };

    setup() {
        this.inputRef = useInputField(this.inputOptions);
        this.state = useState({ value: undefined });
        this.nbsp = nbsp;
        useNumpadDecimal();
        useEffect(() => {
            if (this.inputRef?.el) {
                this.state.value = this.inputRef.el.value;
            }
        });
    }

    /** @returns {{ getValue: () => string | number, refName: string, parse: (v: string) => number }} */
    get inputOptions() {
        return {
            getValue: () => this.formattedValue,
            refName: "numpadDecimal",
            parse: (v) => parseMonetary(v, { allowOperation: true }),
        };
    }

    /** @returns {number | undefined} */
    get currencyId() {
        const currencyField =
            this.props.currencyField ||
            this.props.record.fields[this.props.name].currency_field ||
            "currency_id";
        const currency = this.props.record.data[currencyField];
        return currency && currency.id;
    }
    /** @returns {import("@web/services").Currency | null} */
    get currency() {
        if (!isNaN(this.currencyId)) {
            return getCurrency(this.currencyId) || null;
        }
        return null;
    }

    /** @returns {string} */
    get currencySymbol() {
        return this.currency ? this.currency.symbol : "";
    }

    /** @returns {Array | null} */
    get currencyDigits() {
        if (this.props.useFieldDigits) {
            return this.props.record.fields[this.props.name].digits;
        }
        if (!this.currency) {
            return null;
        }
        return getCurrency(this.currencyId).digits;
    }

    /** @returns {number | false} */
    get value() {
        return this.props.record.data[this.props.name];
    }

    /** @returns {string | number} */
    get formattedValue() {
        if (this.props.inputType === "number" && !this.props.readonly && this.value) {
            return this.value;
        }
        return formatMonetary(this.value, {
            digits: this.currencyDigits,
            minDigits:
                this.props.useFieldDigits &&
                this.props.record.fields[this.props.name].min_display_digits,
            currencyId: this.currencyId,
            noSymbol: !this.props.readonly || this.props.hideSymbol,
            trailingZeros: this.props.trailingZeros,
        });
    }

    /** @param {InputEvent} ev */
    onInput(ev) {
        this.state.value = ev.target.value;
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
        {
            label: _t("Hide trailing zeros"),
            name: "hide_trailing_zeros",
            type: "boolean",
            help: _t(
                "Hide zeros to the right of the last non-zero digit, e.g. 1.20 becomes 1.2",
            ),
        },
    ],
    supportedTypes: ["monetary", "float", "integer"],
    displayName: _t("Monetary"),
    isEmpty: (record, fieldName) => record.data[fieldName] === false,
    extractProps: ({ attrs, options }) => ({
        currencyField: options.currency_field,
        inputType: attrs.type,
        useFieldDigits: options.field_digits,
        hideSymbol: options.no_symbol,
        trailingZeros: !options.hide_trailing_zeros,
    }),
};

registry.category("fields").add("monetary", monetaryField);
