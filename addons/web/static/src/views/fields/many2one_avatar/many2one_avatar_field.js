/** @odoo-module **/

import { registry } from "@web/core/registry";
import { many2OneField, Many2OneField } from "../many2one/many2one_field";

import { Component } from "@odoo/owl";

export class Many2OneAvatarField extends Component {
    static template = "web.Many2OneAvatarField";
    static components = {
        Many2OneField,
    };
    static props = {
        ...Many2OneField.props,
    };

    get relation() {
        return this.props.relation || this.props.record.fields[this.props.name].relation;
    }
    get many2OneProps() {
        return Object.fromEntries(
            Object.entries(this.props).filter(
                ([key, _val]) => key in this.constructor.components.Many2OneField.props
            )
        );
    }
}

export const many2OneAvatarField = {
    ...many2OneField,
    component: Many2OneAvatarField,
};

registry.category("fields").add("many2one_avatar", many2OneAvatarField);
