/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class Many2ManyKanbanTagsField extends Component {}

Many2ManyKanbanTagsField.props = {
    ...standardFieldProps,
};
Many2ManyKanbanTagsField.template = "web.Many2ManyKanbanTagsField";

registry.category("fields").add("kanban.many2many_tags", Many2ManyKanbanTagsField);
