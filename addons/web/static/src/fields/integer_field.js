/** @odoo-module **/

import { registry } from "@web/core/registry";

const { Component } = owl;
export class IntegerField extends Component {
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

registry.category("fields").add("integer", IntegerField);
