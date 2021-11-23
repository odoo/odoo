/** @odoo-module **/

import { registry } from "@web/core/registry";
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
    isEmpty() {
        return false;
    },
});

registry.category("fields").add("boolean_favorite", BooleanFavoriteField);
