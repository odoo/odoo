// @ts-check

/** @module @web/fields/display/stat_info/stat_info_field - Stat button content showing a formatted value with a label */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { exprToBoolean } from "@web/core/utils/format/strings";
import { extractDigits } from "@web/fields/field_utils";
import { standardFieldProps } from "@web/fields/standard_field_props";
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

    /** @returns {string} Field value formatted according to its type and digit precision. */
    get formattedValue() {
        const field = this.props.record.fields[this.props.name];
        const formatter = formatters.get(field.type);
        return formatter(this.props.record.data[this.props.name], {
            digits: this.props.digits,
            field,
        });
    }
    /** @returns {string} Display label from the label field or the static string prop. */
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
    extractProps: ({ attrs, options, string }) => ({
        digits: extractDigits({ attrs, options }),
        labelField: options.label_field,
        noLabel: exprToBoolean(attrs.nolabel),
        string,
    }),
};

registry.category("fields").add("statinfo", statInfoField);
