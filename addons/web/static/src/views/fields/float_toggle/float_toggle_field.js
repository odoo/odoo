/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formatFloat } from "../formatters";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class FloatToggleField extends Component {
    static template = "web.FloatToggleField";
    static props = {
        ...standardFieldProps,
        digits: { type: Array, optional: true },
        range: { type: Array, optional: true },
        factor: { type: Number, optional: true },
        disableReadOnly: { type: Boolean, optional: true },
    };
    static defaultProps = {
        range: [0.0, 0.5, 1.0],
        factor: 1,
        disableReadOnly: false,
    };

    // TODO perf issue (because of update round trip)
    // we probably want to have a state and a useEffect or onWillUpateProps
    onChange() {
        let currentIndex = this.props.range.indexOf(this.props.value * this.factor);
        currentIndex++;
        if (currentIndex > this.props.range.length - 1) {
            currentIndex = 0;
        }
        this.props.record.update({
            [this.props.name]: this.props.range[currentIndex] / this.factor,
        });
    }

    // This property has been created in order to allow overrides in other modules.
    get factor() {
        return this.props.factor;
    }

    get formattedValue() {
        return formatFloat(this.props.value * this.factor, {
            digits: this.props.digits,
        });
    }
}

export const floatToggleField = {
    component: FloatToggleField,
    supportedTypes: ["float"],
    isEmpty: () => false,
    extractProps: ({ attrs, field }) => {
        // Sadly, digits param was available as an option and an attr.
        // The option version could be removed with some xml refactoring.
        let digits;
        if (attrs.digits) {
            digits = JSON.parse(attrs.digits);
        } else if (attrs.options.digits) {
            digits = attrs.options.digits;
        } else if (Array.isArray(field.digits)) {
            digits = field.digits;
        }

        return {
            digits,
            range: attrs.options.range,
            factor: attrs.options.factor,
            disableReadOnly: attrs.options.force_button || false,
        };
    },
};

registry.category("fields").add("float_toggle", floatToggleField);
