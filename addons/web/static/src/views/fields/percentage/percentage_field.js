import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { formatPercentage } from "../formatters";
import { parsePercentage } from "../parsers";
import { useInputField } from "../input_field_hook";
import { useNumpadDecimal } from "../numpad_decimal_hook";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class PercentageField extends Component {
    static template = "web.PercentageField";
    static props = {
        ...standardFieldProps,
        digits: { type: Array, optional: true },
        scale: { type: Number, optional: true },
    };
    static defaultProps = {
        scale: 100,
    };

    setup() {
        if (!Number.isInteger(this.props.scale) || this.props.scale < 1 || this.props.scale > 100) {
            throw new Error("scale must be an integer between 1 and 100");
        }
        useInputField({
            getValue: () =>
                formatPercentage(this.props.record.data[this.props.name], {
                    digits: this.props.digits,
                    scale: this.props.scale,
                    noSymbol: true,
                    field: this.props.record.fields[this.props.name],
                }),
            refName: "numpadDecimal",
            parse: (v) => parsePercentage(v),
        });
        useNumpadDecimal();
    }

    get formattedValue() {
        return formatPercentage(this.props.record.data[this.props.name], {
            digits: this.props.digits,
            scale: this.props.scale,
            field: this.props.record.fields[this.props.name],
        });
    }
}

export const percentageField = {
    component: PercentageField,
    displayName: _t("Percentage"),
    supportedTypes: ["integer", "float"],
    supportedOptions: [
        {
            label: _t("Scale"),
            name: "scale",
            type: "integer",
            help: _t("Scale of the percentage (e.g., 100 for values in [0..1])"),
            default: 100,
            optional: true,
        },
    ],
    extractProps: ({ attrs, options }) => {
        // Sadly, digits param was available as an option and an attr.
        // The option version could be removed with some xml refactoring.
        let digits;
        let scale;
        if (attrs.digits) {
            digits = JSON.parse(attrs.digits);
        } else if (options.digits) {
            digits = options.digits;
        }
        if (options.scale) {
            scale = options.scale;
        }

        return {
            digits,
            scale,
        };
    },
};

registry.category("fields").add("percentage", percentageField);
