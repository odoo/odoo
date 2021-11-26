/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class BooleanFavoriteField extends Component {
    onClick() {
        this.props.update(!this.props.value);
    }
}

Object.assign(BooleanFavoriteField, {
    template: "web.BooleanFavoriteField",
    props: {
        ...standardFieldProps,
    },

    displayName: _lt("Favorite"),
    supportedTypes: ["boolean"],

    isEmpty() {
        return false;
    },
});

registry.category("fields").add("boolean_favorite", BooleanFavoriteField);
