/** @odoo-module **/

import { registry } from "@web/core/registry";
import { InvalidNumberError } from "./parsers";

const { Component, hooks } = owl;
export class FloatField extends Component {
    setup() {
        this.inputRef = hooks.useRef("input");
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

    get inputType() {
        return this.props.options.type === "number" ? "number" : "text";
    }

    get digits() {
        let digits;
        // Sadly, digits param was available as an option and an attr.
        // The option version could be removed with some xml refactoring.
        if (this.props.attrs.digits) {
            digits = JSON.parse(this.props.attrs.digits);
        }
        return digits || this.props.options.digits;
    }

    get formattedValue() {
        return this.props.formatValue(this.props.value, {
            digits: this.digits,
            field: this.props.record.fields[this.props.name],
        });
    }

    get formattedInputValue() {
        if (this.inputType === "number") return this.props.value;
        return this.formattedValue;
    }
}

FloatField.template = "web.FloatField";
FloatField.isEmpty = () => false;

registry.category("fields").add("float", FloatField);
