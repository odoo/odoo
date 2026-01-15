import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { exprToBoolean } from "@web/core/utils/strings";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";
const formatters = registry.category("formatters");

export class StatInfoField extends Component {
    static template = "web.StatInfoField";
    static props = {
        ...standardFieldProps,
        labelField: { type: String, optional: true },
        noLabel: { type: Boolean, optional: true },
        digits: { type: Array, optional: true },
        string: { type: String, optional: true },
    };

    get formattedValue() {
        const field = this.props.record.fields[this.props.name];
        const formatter = formatters.get(field.type);
        return formatter(this.props.record.data[this.props.name], {
            digits: this.props.digits,
            field,
        });
    }
    get label() {
        return this.props.labelField
            ? this.props.record.data[this.props.labelField]
            : this.props.string;
    }
}

export const statInfoField = {
    component: StatInfoField,
    displayName: _t("Stat Info"),
    supportedOptions: [
        {
            label: _t("Label field"),
            name: "label_field",
            type: "field",
            availableTypes: ["char"],
        },
    ],
    supportedTypes: ["float", "integer", "monetary", "char", "one2many", "many2one"],
    isEmpty: () => false,
    extractProps: ({ attrs, options, string }) => {
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
            labelField: options.label_field,
            noLabel: exprToBoolean(attrs.nolabel),
            string,
        };
    },
};

registry.category("fields").add("statinfo", statInfoField);
