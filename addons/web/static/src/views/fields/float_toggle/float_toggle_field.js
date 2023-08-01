/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatFloatFactor } from "../formatters";
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
        let currentIndex = this.props.range.indexOf(
            this.props.record.data[this.props.name] * this.factor
        );
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

    get digits() {
        const fieldDigits = this.props.record.fields[this.props.name].digits;
        return !this.props.digits && Array.isArray(fieldDigits) ? fieldDigits : this.props.digits;
    }
    get formattedValue() {
        return formatFloatFactor(this.props.record.data[this.props.name], {
            digits: this.digits,
            factor: this.factor,
        });
    }
}

export const floatToggleField = {
    component: FloatToggleField,
    supportedOptions: [
        {
            label: _t("Digits"),
            name: "digits",
            type: "string",
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
    extractProps: ({ attrs, options }) => {
        // Sadly, digits param was available as an option and an attr.
        // The option version could be removed with some xml refactoring.
        let digits;
        if (attrs.digits) {
            digits = JSON.parse(attrs.digits);
        } else if (options.digits) {
            digits = options.digits;
        }

        return {
            digits,
            range: options.range,
            factor: options.factor,
            disableReadOnly: options.force_button || false,
        };
    },
};

registry.category("fields").add("float_toggle", floatToggleField);
