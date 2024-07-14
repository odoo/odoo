/** @odoo-module **/

import { registry } from "@web/core/registry";
import {
    KanbanMany2ManyTagsField,
    kanbanMany2ManyTagsField,
} from "@web/views/fields/many2many_tags/kanban_many2many_tags_field";
import {
    Many2ManyTagsField,
    many2ManyTagsField,
} from "@web/views/fields/many2many_tags/many2many_tags_field";

const getDocumentTags = (component, superTags) => {
    if (!component.env.searchModel.getTags) {
        return superTags;
    }
    const searchModelTags = component.env.searchModel.getTags();
    if (!searchModelTags.length) {
        return superTags;
    }
    const searchModelTagByRecordId = searchModelTags.reduce((res, rec) => {
        res[rec.id] = rec;
        return res;
    }, {});
    const recordByTagId = component.props.record.data[component.props.name].records.reduce((res, rec) => {
        res[rec.id] = rec;
        return res;
    }, {});
    return superTags
        .filter((tag) => searchModelTagByRecordId[recordByTagId[tag.id].resId])
        .map((tag) => {
            const record = recordByTagId[tag.id];
            const searchModelTag = searchModelTagByRecordId[record.resId];
            tag.colorIndex = searchModelTag.color_index;
            tag.text = searchModelTag.display_name;
            return tag;
        });
};

// This widget only displays the tags that are currently in the search panel
export class DocumentsKanbanMany2ManyTagsField extends KanbanMany2ManyTagsField {
    get tags() {
        return getDocumentTags(this, super.tags);
    }
}
export const documentsKanbanMany2ManyTagsField = {
    ...kanbanMany2ManyTagsField,
    component: DocumentsKanbanMany2ManyTagsField,
};
registry.category("fields").add("kanban.documents_many2many_tags", documentsKanbanMany2ManyTagsField);

export class DocumentsMany2ManyTagsField extends Many2ManyTagsField {
    get tags() {
        return getDocumentTags(this, super.tags);
    }
}
export const documentsMany2ManyTagsField = {
    ...many2ManyTagsField,
    component: DocumentsMany2ManyTagsField,
};
registry.category("fields").add("documents_many2many_tags", documentsMany2ManyTagsField);
