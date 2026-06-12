import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatFloatFactor } from "../formatters";
import { standardFieldProps } from "../standard_field_props";

import { Component, props, t } from "@odoo/owl";

export class FloatToggleField extends Component {
    static template = "web.FloatToggleField";
    props = props({
        ...standardFieldProps,
        digits: t.array().optional(),
        range: t.array().optional([0.0, 0.5, 1.0]),
        factor: t.number().optional(1),
        disableReadOnly: t.boolean().optional(false),
        trailingZeros: t.boolean().optional(true),
    });

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

    get formattedValue() {
        return formatFloatFactor(this.props.record.data[this.props.name], {
            digits: this.props.digits,
            factor: this.factor,
            field: this.props.record.fields[this.props.name],
            trailingZeros: this.props.trailingZeros,
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
        {
            label: _t("Hide trailing zeros"),
            name: "hide_trailing_zeros",
            type: "boolean",
            help: _t("Hide zeros to the right of the last non-zero digit, e.g. 1.20 becomes 1.2"),
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
            trailingZeros: !options.hide_trailing_zeros,
            range: options.range,
            factor: options.factor,
            disableReadOnly: options.force_button || false,
        };
    },
};

registry.category("fields").add("float_toggle", floatToggleField);
