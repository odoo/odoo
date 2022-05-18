/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatInteger } from "./formatters";
import { parseInteger } from "./parsers";
import { useInputField } from "./input_field_hook";
import { standardFieldProps } from "./standard_field_props";
import { useNumpadDecimal } from "./numpad_decimal_hook";

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
    onChange(ev) {
        let isValid = true;
        let value = ev.target.value;
        try {
            value = parseInteger(value);
        } catch (_e) {
            // WOWL TODO: rethrow error when not the expected type
            isValid = false;
            this.props.setAsInvalid();
        }
        if (isValid) {
            this.props.update(value);
        }
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
    setAsInvalid: { type: Function, optional: true },
};
IntegerField.defaultProps = {
    inputType: "text",
    setAsInvalid: () => {},
};
IntegerField.isEmpty = (record, fieldName) => (record.data[fieldName] === false ? true : false);
IntegerField.extractProps = (fieldName, record, attrs) => {
    return {
        inputType: attrs.options.type,
        step: attrs.options.step,
        setAsInvalid: () => record.setInvalidField(fieldName),
    };
};
IntegerField.displayName = _lt("Integer");
IntegerField.supportedTypes = ["integer"];

registry.category("fields").add("integer", IntegerField);
