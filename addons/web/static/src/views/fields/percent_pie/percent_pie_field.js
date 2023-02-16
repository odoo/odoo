/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class PercentPieField extends Component {
    static template = "web.PercentPieField";
    static props = {
        ...standardFieldProps,
        string: { type: String, optional: true },
    };

    get transform() {
        const rotateDeg = (360 * this.props.value) / 100;
        return {
            left: rotateDeg < 180 ? 180 : rotateDeg,
            right: rotateDeg < 180 ? rotateDeg : 0,
            value: rotateDeg,
        };
    }
}

export const percentPieField = {
    component: PercentPieField,
    displayName: _lt("PercentPie"),
    supportedTypes: ["float", "integer"],
    additionalClasses: ["o_field_percent_pie"],
    extractProps: ({ attrs }) => ({
        string: attrs.string,
    }),
};

registry.category("fields").add("percentpie", percentPieField);
