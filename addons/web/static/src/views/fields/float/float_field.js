/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useInputField } from "../input_field_hook";
import { useNumpadDecimal } from "../numpad_decimal_hook";
import { formatFloat } from "../formatters";
import { parseFloat } from "../parsers";
import { standardFieldProps } from "../standard_field_props";

const { Component } = owl;

export class FloatField extends Component {
    setup() {
        this.inputRef = useInputField({
            getValue: () => this.formattedValue,
            refName: "numpadDecimal",
            parse: (v) => this.parse(v),
        });
        useNumpadDecimal();
    }

    parse(value) {
        return this.props.inputType === "number" ? Number(value) : parseFloat(value);
    }

    get formattedValue() {
        if (this.props.inputType === "number" && !this.props.readonly && this.props.value) {
            return this.props.value;
        }
        return formatFloat(this.props.value, { digits: this.props.digits });
    }
}

FloatField.template = "web.FloatField";
FloatField.props = {
    ...standardFieldProps,
    inputType: { type: String, optional: true },
    step: { type: Number, optional: true },
    digits: { type: Array, optional: true },
    placeholder: { type: String, optional: true },
};
FloatField.defaultProps = {
    inputType: "text",
};

FloatField.displayName = _lt("Float");
FloatField.supportedTypes = ["float"];

FloatField.isEmpty = () => false;
FloatField.extractProps = ({ attrs, field }) => {
    return {
        inputType: attrs.options.type,
        step: attrs.options.step,
        // Sadly, digits param was available as an option and an attr.
        // The option version could be removed with some xml refactoring.
        digits: (attrs.digits ? JSON.parse(attrs.digits) : attrs.options.digits) || field.digits,
        placeholder: attrs.placeholder,
    };
};

registry.category("fields").add("float", FloatField);
