/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { Many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";
import { TagsList } from "../many2many_tags/tags_list";

export class Many2ManyTagsAvatarField extends Many2ManyTagsField {
    get tags() {
        return super.tags.map((tag) => ({
            ...tag,
            img: `/web/image/${this.props.relation}/${tag.resId}/avatar_128`,
            onDelete: !this.props.readonly ? () => this.deleteTag(tag.id) : undefined,
        }));
    }
}

Many2ManyTagsAvatarField.template = "web.Many2ManyTagsAvatarField";
Many2ManyTagsAvatarField.components = {
    Many2XAutocomplete,
    TagsList,
};

registry.category("fields").add("many2many_tags_avatar", Many2ManyTagsAvatarField);

export class ListKanbanMany2ManyTagsAvatarField extends Many2ManyTagsAvatarField {
    get itemsVisible() {
        return this.props.record.activeFields[this.props.name].viewType === "list" ? 5 : 3;
    }

    getTagProps(record) {
        return {
            ...super.getTagProps(record),
            img: `/web/image/${this.props.relation}/${record.resId}/avatar_128`,
        };
    }
}

registry.category("fields").add("list.many2many_tags_avatar", ListKanbanMany2ManyTagsAvatarField);
registry.category("fields").add("kanban.many2many_tags_avatar", ListKanbanMany2ManyTagsAvatarField);
