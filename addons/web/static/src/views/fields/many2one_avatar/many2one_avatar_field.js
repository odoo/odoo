/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Domain } from "@web/core/domain";
import { Many2OneField } from "../many2one/many2one_field";
import { standardFieldProps } from "../standard_field_props";

const { Component } = owl;

export class Many2OneAvatarField extends Component {}

Many2OneAvatarField.template = "web.Many2OneAvatarField";
Many2OneAvatarField.components = {
    Many2OneField,
};
Many2OneAvatarField.props = {
    ...standardFieldProps,
    relation: String,
    getContext: { type: Function, optional: true },
    getDomain: { type: Function, optional: true },
};
Many2OneAvatarField.defaultProps = {
    getContext: () => ({}),
    getDomain: () => new Domain(),
};

Many2OneAvatarField.supportedTypes = ["many2one"];

Many2OneAvatarField.extractProps = (fieldName, record) => {
    return {
        relation: record.fields[fieldName].relation,
        getContext: () => record.getFieldContext(fieldName),
        getDomain: () => record.getFieldDomain(fieldName),
    };
};

registry.category("fields").add("many2one_avatar", Many2OneAvatarField);
