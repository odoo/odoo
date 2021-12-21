/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";
import { Many2ManyTagsField } from "./many2many_tags_field";

export class KanbanMany2ManyTagsField extends Many2ManyTagsField {}

KanbanMany2ManyTagsField.props = {
    ...standardFieldProps,
};
KanbanMany2ManyTagsField.template = "web.KanbanMany2ManyTagsField";

registry.category("fields").add("kanban.many2many_tags", KanbanMany2ManyTagsField);
