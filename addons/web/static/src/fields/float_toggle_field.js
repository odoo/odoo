/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formatFloat } from "./formatters";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class FloatToggleField extends Component {
    // TODO perf issue (because of update round trip)
    // we probably want to have a state and a useEffect or onWillUpateProps
    onChange() {
        let currentIndex = this.props.range.indexOf(this.props.value * this.props.factor);
        currentIndex++;
        if (currentIndex > this.props.range.length - 1) {
            currentIndex = 0;
        }
        this.props.update(this.props.range[currentIndex] / this.props.factor);
    }

    get formattedValue() {
        return formatFloat(this.props.value * this.props.factor, {
            digits: this.props.digits,
        });
    }
}

FloatToggleField.template = "web.FloatToggleField";
FloatToggleField.props = {
    ...standardFieldProps,
    digits: { type: Array, optional: true },
    range: { type: Array, optional: true },
    factor: { type: Number, optional: true },
    disableReadOnly: { type: Boolean, optional: true },
};
FloatToggleField.defaultProps = {
    range: [0.0, 0.5, 1.0],
    factor: 1,
    disableReadOnly: false,
};

FloatToggleField.supportedTypes = ["float"];

FloatToggleField.isEmpty = () => false;
FloatToggleField.extractProps = (fieldName, record, attrs) => {
    return {
        digits:
            (attrs.digits ? JSON.parse(attrs.digits) : attrs.options.digits) ||
            record.fields[fieldName].digits,
        range: attrs.options.range,
        factor: attrs.options.factor,
        disableReadOnly: attrs.options.force_button || false,
    };
};

registry.category("fields").add("float_toggle", FloatToggleField);
