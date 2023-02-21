/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { archParseBoolean } from "@web/views/utils";
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
    };

    get formattedValue() {
        const formatter = formatters.get(this.props.record.fields[this.props.name].type);
        return formatter(this.props.value || 0, { digits: this.props.digits });
    }
    get label() {
        return this.props.labelField
            ? this.props.record.data[this.props.labelField]
            : this.props.record.activeFields[this.props.name].string;
    }
}

export const statInfoField = {
    component: StatInfoField,
    displayName: _lt("Stat Info"),
    supportedTypes: ["float", "integer", "monetary"],
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
            labelField: attrs.options.label_field,
            noLabel: archParseBoolean(attrs.nolabel),
        };
    },
};

registry.category("fields").add("statinfo", statInfoField);
