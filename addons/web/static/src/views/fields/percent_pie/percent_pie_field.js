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
}

export const percentPieField = {
    component: PercentPieField,
    displayName: _lt("PercentPie"),
    supportedTypes: ["float", "integer"],
    additionalClasses: ["o_field_percent_pie"],
    extractProps: ({ string }) => ({ string }),
};

registry.category("fields").add("percentpie", percentPieField);
