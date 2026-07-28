/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { formatFloat } from "../formatters";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class PercentPieField extends Component {
    static template = "web.PercentPieField";
    static props = {
        ...standardFieldProps,
        string: { type: String, optional: true },
    };

    /**
     * Format to 2 decimals without trailing zeros.
     */
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
