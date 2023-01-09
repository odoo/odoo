/** @odoo-module **/

import fieldRegistry from 'web.field_registry';
import { FieldChar } from 'web.basic_fields';

export const FieldNameWithSubTaskCount = FieldChar.extend({
    /**
     * @override
     */
    init() {
        this._super(...arguments);
        if (this.viewType === 'kanban') {
            // remove click event handler
            this.events = { ...this.events };
            delete this.events.click;
        }
    },

    _render: function () {
        let result = this._super.apply(this, arguments);
        if (this.recordData.allow_subtasks && this.recordData.child_text) {
            this.$el.append($('<span>')
                    .addClass("text-muted ms-2")
                    .text(this.recordData.child_text)
                    .css('font-weight', 'normal'));
        }
        return result;
    }
});

fieldRegistry.add('name_with_subtask_count', FieldNameWithSubTaskCount);
