/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2ManyTagsField } from "./many2many_tags_field";

export class KanbanMany2ManyTagsField extends Many2ManyTagsField {
    get tags() {
        return super.tags.reduce((kanbanTags, tag) => {
            if (tag.colorIndex !== 0) {
                delete tag.onClick;
                kanbanTags.push(tag);
            }
            return kanbanTags;
        }, []);
    }
}

KanbanMany2ManyTagsField.template = "web.KanbanMany2ManyTagsField";

registry.category("fields").add("kanban.many2many_tags", KanbanMany2ManyTagsField);
