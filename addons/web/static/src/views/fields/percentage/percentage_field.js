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
            getValue: () => this.props.value * 100,
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
    invalidate: { type: Function, optional: true },
    digits: { type: Array, optional: true },
};
PercentageField.defaultProps = {
    invalidate: () => {},
};

PercentageField.displayName = _lt("Percentage");
PercentageField.supportedTypes = ["integer", "float"];

PercentageField.extractProps = (fieldName, record, attrs) => {
    return {
        invalidate: () => record.setInvalidField(fieldName),
        digits:
            (attrs.digits ? JSON.parse(attrs.digits) : attrs.options.digits) ||
            record.fields[fieldName].digits,
    };
};

registry.category("fields").add("percentage", PercentageField);
