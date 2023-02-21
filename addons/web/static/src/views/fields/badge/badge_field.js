/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";
const formatters = registry.category("formatters");

export class BadgeField extends Component {
    static template = "web.BadgeField";
    static props = {
        ...standardFieldProps,
    };

    get formattedValue() {
        const formatter = formatters.get(this.props.record.fields[this.props.name].type);
        return formatter(this.props.value, {
            selection: this.props.record.fields[this.props.name].selection,
        });
    }

    get classFromDecoration() {
        for (const decorationName in this.props.decorations) {
            if (this.props.decorations[decorationName]) {
                return `text-bg-${decorationName}`;
            }
        }
        return "";
    }
}

export const badgeField = {
    component: BadgeField,
    displayName: _lt("Badge"),
    supportedTypes: ["selection", "many2one", "char"],
};

registry.category("fields").add("badge", badgeField);
