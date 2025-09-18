// @ts-check

/** @module @web/fields/display/percent_pie/percent_pie_field - Pie chart visualization showing a percentage value */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatFloat } from "@web/fields/formatters";
import { standardFieldProps } from "@web/fields/standard_field_props";

export class PercentPieField extends Component {
    static template = "web.PercentPieField";
    static props = {
        ...standardFieldProps,
        string: { type: String, optional: true },
    };

    /** @returns {string} Value formatted to 2 decimals without trailing zeros. */
    get formattedValue() {
        return formatFloat(this.props.record.data[this.props.name], {
            trailingZeros: false,
        });
    }
}

export const percentPieField = {
    component: PercentPieField,
    displayName: _t("PercentPie"),
    supportedTypes: ["float", "integer"],
    additionalClasses: ["o_field_percent_pie"],
    extractProps: ({ string }) => ({ string }),
};

registry.category("fields").add("percentpie", percentPieField);
