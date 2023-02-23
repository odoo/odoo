/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { archParseBoolean } from "@web/views/utils";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class BooleanFavoriteField extends Component {
    static template = "web.BooleanFavoriteField";
    static props = {
        ...standardFieldProps,
        noLabel: { type: Boolean, optional: true },
    };
    static defaultProps = {
        noLabel: false,
    };

    update() {
        this.props.record.update({ [this.props.name]: !this.props.value });
    }
}

export const booleanFavoriteField = {
    component: BooleanFavoriteField,
    displayName: _lt("Favorite"),
    supportedTypes: ["boolean"],
    isEmpty: () => false,
    extractProps: ({ attrs }) => ({
        noLabel: archParseBoolean(attrs.nolabel),
    }),
};

registry.category("fields").add("boolean_favorite", booleanFavoriteField);
