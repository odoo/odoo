/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";
import { Many2OneField } from "./many2one_field";

const { Component } = owl;

export class Many2OneAvatarField extends Component {}

Many2OneAvatarField.template = "web.Many2OneAvatarField";
Many2OneAvatarField.props = {
    ...standardFieldProps,
    placeholder: { type: String, optional: true },
    relation: Object,
};
Many2OneAvatarField.extractProps = (fieldName, record) => {
    return {
        relation: record.fields[fieldName].relation,
    };
};
Many2OneAvatarField.components = {
    Many2OneField,
};
Many2OneAvatarField.supportedTypes = ["many2one"];

registry.category("fields").add("many2one_avatar", Many2OneAvatarField);
