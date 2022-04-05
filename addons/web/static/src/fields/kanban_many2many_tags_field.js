/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2ManyTagsField } from "./many2many_tags_field";

class KanbanMany2ManyTagsField extends Many2ManyTagsField {
    get tags() {
        return super.tags.filter((tag) => tag.colorIndex !== 0);
    }
}
KanbanMany2ManyTagsField.template = "web.KanbanMany2ManyTagsField";
registry.category("fields").add("kanban.many2many_tags", KanbanMany2ManyTagsField);
