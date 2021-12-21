/** @odoo-module **/

import { registry } from "@web/core/registry";

const { Component, hooks } = owl;
export class FloatField extends Component {
    setup() {
        this.inputRef = hooks.useRef("input");
    }

    onChange(ev) {
        const parsedValue = this.props.parseValue(ev.target.value);

        // Needed cause the formatting was causing owl to not be able any change in the DOM.
        // ex: If we want 3 digits after the decimal
        // input: 1.500  DOM: 1.500
        // input changed to 1.5000, comes back formatted as 1.500.
        // => the DOM comparaison sees no difference. But the input value displayed is still 1.5000.
        this.inputRef.el.value = this.formattedInputValue;

        this.props.update(parsedValue);
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
