/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";

export class BooleanIconField extends Component {
    static template = "web.BooleanIconField";
    static props = {
        ...standardFieldProps,
        icon: { type: String, optional: true },
        label: { type: String, optional: true },
    };
    static defaultProps = {
        icon: "fa-check-square-o",
    };

    update() {
        this.props.record.update({ [this.props.name]: !this.props.value });
    }
}

export const booleanIconField = {
    component: BooleanIconField,
    displayName: _lt("Boolean Icon"),
    supportedTypes: ["boolean"],
    extractProps: ({ options, string }) => ({
        icon: options.icon,
        label: string,
    }),
};

registry.category("fields").add("boolean_icon", booleanIconField);
