/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useInputField } from "../input_field_hook";
import { useNumpadDecimal } from "../numpad_decimal_hook";
import { formatFloat } from "../formatters";
import { parseFloat } from "../parsers";
import { standardFieldProps } from "../standard_field_props";

const { Component, onWillUpdateProps } = owl;

export class FloatField extends Component {
    setup() {
        this.defaultInputValue = this.getFormattedValue();
        useInputField({
            getValue: () => this.defaultInputValue,
            refName: "numpadDecimal",
            parse: (v) => this.parse(v),
        });
        useNumpadDecimal();
        onWillUpdateProps((nextProps) => {
            if (
                nextProps.readonly !== this.props.readonly &&
                !nextProps.readonly &&
                nextProps.inputType !== "number"
            ) {
                this.defaultInputValue = this.getFormattedValue(nextProps);
            }
        });
    }

    parse(value) {
        return this.props.inputType === "number" ? Number(value) : parseFloat(value);
    }

    onChange(ev) {
        this.defaultInputValue = ev.target.value;
    }

    getFormattedValue(props = this.props) {
        if (props.inputType === "number" && !props.readonly && props.value) {
            return props.value;
        }
        return formatFloat(props.value, { digits: props.digits });
    }
}

FloatField.template = "web.FloatField";
FloatField.props = {
    ...standardFieldProps,
    inputType: { type: String, optional: true },
    step: { type: Number, optional: true },
    digits: { type: Array, optional: true },
    invalidate: { type: Function, optional: true },
};
FloatField.defaultProps = {
    inputType: "text",
    invalidate: () => {},
};

FloatField.displayName = _lt("Float");
FloatField.supportedTypes = ["float"];

FloatField.isEmpty = () => false;
FloatField.extractProps = (fieldName, record, attrs) => {
    return {
        invalidate: () => record.setInvalidField(fieldName),
        inputType: attrs.options.type,
        step: attrs.options.step,
        // Sadly, digits param was available as an option and an attr.
        // The option version could be removed with some xml refactoring.
        digits:
            (attrs.digits ? JSON.parse(attrs.digits) : attrs.options.digits) ||
            record.fields[fieldName].digits,
    };
};

registry.category("fields").add("float", FloatField);
