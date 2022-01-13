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
        noLabel: { type: Boolean, optional: true },
    },
    defaultProps: {
        noLabel: false,
    },

    displayName: _lt("Favorite"),
    supportedTypes: ["boolean"],

    isEmpty() {
        return false;
    },

    convertAttrsToProps(attrs) {
        return {
            noLabel: Boolean(attrs.nolabel && !/^(0|false)$/i.test(attrs.nolabel)),
        };
    },
});

registry.category("fields").add("boolean_favorite", BooleanFavoriteField);
