import { Many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";
import { KanbanMany2ManyTagsField } from "@web/views/fields/many2many_tags/kanban_many2many_tags_field";
import { patch } from "@web/core/utils/patch";


/**
 * @override to avoid KanbanMany2ManyTagsField filtering of tags based on color index in Documents.
 * todo: replace with cleaner solution in master
 */
patch(KanbanMany2ManyTagsField.prototype, {
    get tags() {
        if (this.props.record._config.resModel === 'documents.document') {
            return Object.getOwnPropertyDescriptor(Many2ManyTagsField.prototype, 'tags').get.call(this);
        }
        return super.tags;
    }
});
