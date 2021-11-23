/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class KanbanMany2ManyTagsField extends Component {}

KanbanMany2ManyTagsField.props = {
    ...standardFieldProps,
};
KanbanMany2ManyTagsField.template = "web.KanbanMany2ManyTagsField";

registry.category("fields").add("kanban.many2many_tags", KanbanMany2ManyTagsField);
