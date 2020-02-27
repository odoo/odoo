odoo.define('project.update_kanban', function (require) {
'use strict';

var KanbanRecord = require('web.KanbanRecord');
var basic_fields = require('web.basic_fields');
var registry = require('web.field_registry');

KanbanRecord.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _openRecord: function () {
        if (this.modelName === 'project.project' && this.$(".o_project_kanban_boxes a").length) {
            this.$('.o_project_kanban_boxes a').first().click();
        } else {
            this._super.apply(this, arguments);
        }
    },

});

var FieldTaskClosedDeadline = basic_fields.FieldDate.extend({
    _renderReadonly: function () {
        if (this.value && this.value.toISOString()) {
            var deadline = moment(this.value.toISOString()).startOf('day');
            var task_closed = 'is_closed' in this.record.data && this.record.data.is_closed;

            if (!task_closed && deadline < moment().startOf('day')) {
                this.$el.addClass('text-danger font-weight-bold');
            } else if (!task_closed && deadline < moment().endOf('day')) {
                this.$el.addClass('text-warning font-weight-bold');
            }
        }

        this.$el.text(this._formatValue(this.value));
    }
});

registry.add('task_closed_deadline', FieldTaskClosedDeadline);

return FieldTaskClosedDeadline;
});
