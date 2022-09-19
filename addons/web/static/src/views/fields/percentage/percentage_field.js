/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { formatPercentage } from "../formatters";
import { parsePercentage } from "../parsers";
import { useInputField } from "../input_field_hook";
import { useNumpadDecimal } from "../numpad_decimal_hook";
import { standardFieldProps } from "../standard_field_props";

const { Component } = owl;

export class PercentageField extends Component {
    setup() {
        useInputField({
            getValue: () =>
                formatPercentage(this.props.value, {
                    digits: this.props.digits,
                    noSymbol: true,
                }),
            refName: "numpadDecimal",
            parse: (v) => parsePercentage(v),
        });
        useNumpadDecimal();
    }

    get formattedValue() {
        return formatPercentage(this.props.value, {
            digits: this.props.digits,
        });
    }
}

PercentageField.template = "web.PercentageField";
PercentageField.props = {
    ...standardFieldProps,
    digits: { type: Array, optional: true },
    placeholder: { type: String, optional: true },
};

PercentageField.displayName = _lt("Percentage");
PercentageField.supportedTypes = ["integer", "float"];

PercentageField.extractProps = ({ attrs, field }) => {
    return {
        digits: (attrs.digits ? JSON.parse(attrs.digits) : attrs.options.digits) || field.digits,
        placeholder: attrs.placeholder,
    };
};

registry.category("fields").add("percentage", PercentageField);
