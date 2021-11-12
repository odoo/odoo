/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class Many2ManyTagsField extends Component {
    setup() {
        const dataList = this.props.record.data[this.props.name];
        this.data = (dataList && dataList.data) || [];
    }
}

Many2ManyTagsField.fieldsToFetch = {
    display_name: { type: "char" },
};
Many2ManyTagsField.props = {
    ...standardFieldProps,
    placeholder: { type: String, optional: true },
};
Many2ManyTagsField.template = "web.Many2ManyTagsField";

registry.category("fields").add("many2many_tags", Many2ManyTagsField);
