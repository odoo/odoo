/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component, useRef } = owl;
export class FloatField extends Component {
    setup() {
        this.inputRef = useRef("input");
    }

    onChange(ev) {
        let isValid = true;
        let value = ev.target.value;
        try {
            value = this.props.parseValue(value);
        } catch (e) {
            isValid = false;
            this.props.record.setInvalidField(this.props.name);
        }
        if (isValid) {
            this.props.update(value);
        }
    }

    get formattedValue() {
        return this.props.formatValue(this.props.value, {
            digits: this.props.digits,
            field: this.props.record.fields[this.props.name],
        });
    }

    get formattedInputValue() {
        if (this.props.inputType === "number") {
            return this.props.value;
        }
        return this.formattedValue;
    }
}

FloatField.template = "web.FloatField";
FloatField.props = {
    ...standardFieldProps,
    inputType: { type: String, optional: true },
    digits: { type: Array, optional: true },
};
FloatField.defaultProps = {
    inputType: "text",
};
FloatField.isEmpty = () => false;
FloatField.convertAttrsToProps = (attrs) => {
    return {
        inputType: attrs.type,
        // Sadly, digits param was available as an option and an attr.
        // The option version could be removed with some xml refactoring.
        digits: attrs.digits ? JSON.parse(attrs.digits) : attrs.options.digits,
    };
};

registry.category("fields").add("float", FloatField);
