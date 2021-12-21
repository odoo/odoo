/** @odoo-module **/

import { registry } from "@web/core/registry";

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
        return this.props.formatValue(this.props.value);
    }
}

IntegerField.template = "web.IntegerField";
IntegerField.isEmpty = () => false;

registry.category("fields").add("integer", IntegerField);
