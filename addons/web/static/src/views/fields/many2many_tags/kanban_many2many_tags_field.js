import { registry } from "@web/core/registry";
import { Many2ManyTagsField, many2ManyTagsField } from "./many2many_tags_field";

export class KanbanMany2ManyTagsField extends Many2ManyTagsField {
    static template = "web.KanbanMany2ManyTagsField";

    get tags() {
        return super.tags.filter((tag) => tag.props.color !== 0);
    }
}

export const kanbanMany2ManyTagsField = {
    ...many2ManyTagsField,
    component: KanbanMany2ManyTagsField,
};

registry.category("fields").add("kanban.many2many_tags", kanbanMany2ManyTagsField);
