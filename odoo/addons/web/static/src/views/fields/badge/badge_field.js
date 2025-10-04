/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component } from "@odoo/owl";
const formatters = registry.category("formatters");

export class BadgeField extends Component {
    static template = "web.BadgeField";
    static props = {
        ...standardFieldProps,
        decorations: { type: Object, optional: true },
    };
    static defaultProps = {
        decorations: {},
    };

    get formattedValue() {
        const formatter = formatters.get(this.props.record.fields[this.props.name].type);
        return formatter(this.props.record.data[this.props.name], {
            selection: this.props.record.fields[this.props.name].selection,
        });
    }

    get classFromDecoration() {
        const evalContext = this.props.record.evalContextWithVirtualIds;
        for (const decorationName in this.props.decorations) {
            if (evaluateBooleanExpr(this.props.decorations[decorationName], evalContext)) {
                return `text-bg-${decorationName}`;
            }
        }
        return "";
    }
}

export const badgeField = {
    component: BadgeField,
    displayName: _t("Badge"),
    supportedTypes: ["selection", "many2one", "char"],
    extractProps: ({ decorations }) => {
        return { decorations };
    },
};

registry.category("fields").add("badge", badgeField);
