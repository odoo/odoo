import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { formatPercentage } from "../formatters";
import { parsePercentage } from "../parsers";
import { useInputField } from "../input_field_hook";
import { useNumpadDecimal } from "../numpad_decimal_hook";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class PercentageField extends Component {
    static template = "web.PercentageField";
    static props = {
        ...standardFieldProps,
        digits: { type: Array, optional: true },
        placeholder: { type: String, optional: true },
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
            digits,
            placeholder: attrs.placeholder,
        };
    },
};

registry.category("fields").add("percentage", percentageField);
