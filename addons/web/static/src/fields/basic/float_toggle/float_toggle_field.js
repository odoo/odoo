// @ts-check

/** @module @web/fields/basic/float_toggle/float_toggle_field - Cyclic button that steps through a list of float values on click */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { extractDigits } from "@web/fields/field_utils";
import { formatFloatFactor } from "@web/fields/formatters";
import { standardFieldProps } from "@web/fields/standard_field_props";

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
    /** Advances to the next value in the range cycle and updates the record. */
    onChange() {
        let currentIndex = this.props.range.indexOf(
            this.props.record.data[this.props.name] * this.factor,
        );
        currentIndex++;
        if (currentIndex > this.props.range.length - 1) {
            currentIndex = 0;
        }
        this.props.record.update({
            [this.props.name]: this.props.range[currentIndex] / this.factor,
        });
    }

    /** @returns {number} multiplication factor (overridable by subclasses) */
    get factor() {
        return this.props.factor;
    }

    /** @returns {string} display value formatted with factor and digits */
    get formattedValue() {
        return formatFloatFactor(this.props.record.data[this.props.name], {
            digits: this.props.digits,
            factor: this.factor,
            field: this.props.record.fields[this.props.name],
        });
    }
}

export const floatToggleField = {
    component: FloatToggleField,
    supportedOptions: [
        {
            label: _t("Digits"),
            name: "digits",
            type: "digits",
        },
        {
            label: _t("Type"),
            name: "type",
            type: "string",
        },
        {
            label: _t("Range"),
            name: "range",
            type: "string",
        },
        {
            label: _t("Factor"),
            name: "factor",
            type: "number",
        },
        {
            label: _t("Disable readonly"),
            name: "force_button",
            type: "boolean",
        },
    ],
    supportedTypes: ["float"],
    isEmpty: () => false,
    extractProps: ({ attrs, options }) => ({
        digits: extractDigits({ attrs, options }),
        range: options.range,
        factor: options.factor,
        disableReadOnly: options.force_button || false,
    }),
};

registry.category("fields").add("float_toggle", floatToggleField);
