/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Field } from "./field";

const { Component } = owl;
export class IntegerField extends Component {
    onChange(ev) {
        const parsedValue = this.props.parseValue(ev.target.value);
        this.props.update(parsedValue);
    }

    get inputType() {
        return this.props.options.type === "number" ? "number" : "text";
    }

    get formattedInputValue() {
        if (this.inputType === "number") return this.props.value;
        return this.props.formatValue(this.props.value, {
            field: this.props.record.fields[this.props.name],
        });
    }
}

IntegerField.template = "web.IntegerField";
IntegerField.isEmpty = () => false;
IntegerField.isValid = (value) => Number.isInteger(Field.parseFieldValue(value));

registry.category("fields").add("integer", IntegerField);
