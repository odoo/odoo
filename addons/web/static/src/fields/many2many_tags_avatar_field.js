/** @odoo-module **/

import { registry } from "@web/core/registry";
import { TagsList } from "@web/core/tags/tags_list";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { Many2ManyTagsField } from "./many2many_tags_field";

export class Many2ManyTagsAvatarField extends Many2ManyTagsField {
    get tags() {
        return this.props.value.records.map((record) => ({
            id: record.id, // datapoint_X
            text: record.data.display_name,
            img: `/web/image/${this.props.relation}/${record.resId}/avatar_128`,
            onDelete: !this.props.readonly ? () => this.onDelete(record.resId) : undefined,
        }));
    }
}

Many2ManyTagsAvatarField.components = {
    AutoComplete,
    TagsList,
};
Many2ManyTagsAvatarField.template = "web.Many2ManyTagsAvatarField";
Many2ManyTagsAvatarField.extractProps = (fieldName, record, attrs) => {
    return {
        relation: record.activeFields[fieldName].relation,
        domain: record.getFieldDomain(fieldName),
        context: record.getFieldContext(fieldName),
        canQuickCreate: !attrs.options.no_quick_create,
    };
};
Many2ManyTagsAvatarField.supportedTypes = ["many2many"];

registry.category("fields").add("many2many_tags_avatar", Many2ManyTagsAvatarField);

class ListKanbanMany2ManyTagsAvatarField extends Many2ManyTagsAvatarField {
    setup() {
        super.setup();
        this.visibleTags =
            this.props.record.activeFields[this.props.name].viewType === "list" ? 5 : 3;
    }
    get tags() {
        return this.props.value.records.map((record) => ({
            id: record.id, // datapoint_X
            text: record.data.display_name,
            img: `/web/image/${this.props.relation}/${record.resId}/avatar_128`,
        }));
    }
}

registry.category("fields").add("list.many2many_tags_avatar", ListKanbanMany2ManyTagsAvatarField);
registry.category("fields").add("kanban.many2many_tags_avatar", ListKanbanMany2ManyTagsAvatarField);
