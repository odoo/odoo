/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class FavoriteField extends Component {
    onClick() {
        this.props.update(!this.props.value);
    }
}

Object.assign(FavoriteField, {
    template: "web.FavoriteField",
    props: {
        ...standardFieldProps,
    },
    isEmpty() {
        return false;
    },
});

registry.category("fields").add("boolean_favorite", FavoriteField);
