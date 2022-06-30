/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { Many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";
import { TagsList } from "../many2many_tags/tags_list";

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

Many2ManyTagsAvatarField.template = "web.Many2ManyTagsAvatarField";
Many2ManyTagsAvatarField.components = {
    Many2XAutocomplete,
    TagsList,
};

Many2ManyTagsAvatarField.supportedTypes = ["many2many"];

Many2ManyTagsAvatarField.extractProps = (fieldName, record, attrs) => {
    return {
        relation: record.activeFields[fieldName].relation,
        domain: record.getFieldDomain(fieldName),
        context: record.getFieldContext(fieldName),
        evalContext: record.evalContext,
        canQuickCreate: !attrs.options.no_quick_create,
        createDomain: attrs.options.create,
        string: record.activeFields[fieldName].string,
    };
};

registry.category("fields").add("many2many_tags_avatar", Many2ManyTagsAvatarField);

class ListKanbanMany2ManyTagsAvatarField extends Many2ManyTagsAvatarField {
    get tags() {
        return this.props.value.records.map((record) => ({
            id: record.id, // datapoint_X
            text: record.data.display_name,
            img: `/web/image/${this.props.relation}/${record.resId}/avatar_128`,
        }));
    }
}

ListKanbanMany2ManyTagsAvatarField.extractProps = (fieldName, record, attrs) => {
    return {
        itemsVisible: record.activeFields[fieldName].viewType === "list" ? 5 : 3,
        relation: record.activeFields[fieldName].relation,
        domain: record.getFieldDomain(fieldName),
        context: record.getFieldContext(fieldName),
        evalContext: record.evalContext,
        canQuickCreate: !attrs.options.no_quick_create,
        createDomain: attrs.options.create,
        string: record.activeFields[fieldName].string,
    };
};

registry.category("fields").add("list.many2many_tags_avatar", ListKanbanMany2ManyTagsAvatarField);
registry.category("fields").add("kanban.many2many_tags_avatar", ListKanbanMany2ManyTagsAvatarField);
