// @ts-check

/** @module @web/fields/basic/percentage/percentage_field - Numeric input field that displays and parses percentage values */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { extractDigits } from "@web/fields/field_utils";
import { formatPercentage } from "@web/fields/formatters";
import { useInputField } from "@web/fields/input_field_hook";
import { useNumpadDecimal } from "@web/fields/numpad_decimal_hook";
import { parsePercentage } from "@web/fields/parsers";
import { standardFieldProps } from "@web/fields/standard_field_props";

export class PercentageField extends Component {
    static template = "web.PercentageField";
    static props = {
        ...standardFieldProps,
        digits: { type: Array, optional: true },
    };

    setup() {
        useInputField({
            getValue: () =>
                formatPercentage(this.props.record.data[this.props.name], {
                    digits: this.props.digits,
                    noSymbol: true,
                    field: this.props.record.fields[this.props.name],
                }),
            refName: "numpadDecimal",
            parse: (v) => parsePercentage(v),
        });
        useNumpadDecimal();
    }

    /** @returns {string} value formatted as percentage with symbol */
    get formattedValue() {
        return formatPercentage(this.props.record.data[this.props.name], {
            digits: this.props.digits,
            field: this.props.record.fields[this.props.name],
        });
    }
}

export const percentageField = {
    component: PercentageField,
    displayName: _t("Percentage"),
    supportedTypes: ["integer", "float"],
    extractProps: ({ attrs, options }) => ({
        digits: extractDigits({ attrs, options }),
    }),
};

registry.category("fields").add("percentage", percentageField);
