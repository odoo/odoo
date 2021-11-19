/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class Many2ManyTagsField extends Component {
    get tags() {
        return this.props.value.records.map((record) => ({
            id: record.data.id,
            name: record.data.display_name,
            color: record.data.color,
        }));
    }
}

Many2ManyTagsField.fieldsToFetch = {
    display_name: { name: "display_name", type: "char" },
};
Many2ManyTagsField.props = {
    ...standardFieldProps,
    placeholder: { type: String, optional: true },
};
Many2ManyTagsField.template = "web.Many2ManyTagsField";

registry.category("fields").add("many2many_tags", Many2ManyTagsField);
