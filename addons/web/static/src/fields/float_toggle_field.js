/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;
export class FloatToggleField extends Component {

    // TODO perf issue (because of update round trip)
    // we probably want to have a state and a useEffect or onWillUpateProps
    onChange(ev) {
        let currentIndex = this.props.range.indexOf(this.props.value)
        currentIndex++;
        if (currentIndex > this.props.range.length - 1) {
            currentIndex = 0;
        }
        this.props.update(this.props.range[currentIndex] / this.props.factor);
    }

    get formattedValue() {
        return this.props.format(this.props.value * this.props.factor, {
            digits: this.props.digits,
        });
    }

}

FloatToggleField.template = "web.FloatToggleField";
FloatToggleField.props = {
    ...standardFieldProps,
    digits: { type: Array, optional: true },
    setAsInvalid: { type: Function, optional: true },
    range: { type: Array, optional: true },
    factor: { type: Number, optional: true },
};
FloatToggleField.defaultProps = {
    setAsInvalid: () => {},
    range:  [0.0, 0.5, 1.0],
    factor: 1,
};
FloatToggleField.isEmpty = () => false;
FloatToggleField.extractProps = (fieldName, record, attrs) => {
    return {
        digits:
            (attrs.digits ? JSON.parse(attrs.digits) : attrs.options.digits) ||
            record.fields[fieldName].digits,
        range: attrs.options.range,
        factor: attrs.options.factor,
    };
};

registry.category("fields").add("float_toggle", FloatToggleField);
