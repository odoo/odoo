/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class Many2ManyTagsField extends Component {
    get tags() {
        const colorField = this.props.options.color_field;
        return this.props.value.records
            .filter((record) => !colorField || record.data[colorField])
            .map((record, i) => ({
                id: record.data.id,
                name: record.data.display_name,
                colorIndex: record.data[colorField] || i,
            }));
    }
}

Object.assign(Many2ManyTagsField, {
    template: "web.Many2ManyTagsField",
    props: {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    },

    displayName: _lt("Tags"),
    supportedTypes: ["many2many"],

    fieldsToFetch: {
        display_name: { name: "display_name", type: "char" },
    },
});

registry.category("fields").add("many2many_tags", Many2ManyTagsField);
