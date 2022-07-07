/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatInteger } from "../formatters";
import { parseInteger } from "../parsers";
import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";
import { useNumpadDecimal } from "../numpad_decimal_hook";

const { Component } = owl;

export class IntegerField extends Component {
    setup() {
        useInputField({
            getValue: () => this.formattedValue,
            refName: "numpadDecimal",
            parse: (v) => parseInteger(v),
        });
        useNumpadDecimal();
    }

    get formattedValue() {
        if (!this.props.readonly && this.props.inputType === "number") {
            return this.props.value;
        }
        return formatInteger(this.props.value);
    }
}

IntegerField.template = "web.IntegerField";
IntegerField.props = {
    ...standardFieldProps,
    inputType: { type: String, optional: true },
    step: { type: Number, optional: true },
    invalidate: { type: Function, optional: true },
    placeholder: { type: String, optional: true },
};
IntegerField.defaultProps = {
    inputType: "text",
    invalidate: () => {},
};

IntegerField.displayName = _lt("Integer");
IntegerField.supportedTypes = ["integer"];

IntegerField.isEmpty = (record, fieldName) => (record.data[fieldName] === false ? true : false);
IntegerField.extractProps = (fieldName, record, attrs) => {
    return {
        inputType: attrs.options.type,
        step: attrs.options.step,
        invalidate: () => record.setInvalidField(fieldName),
        placeholder: attrs.placeholder,
    };
};

registry.category("fields").add("integer", IntegerField);
