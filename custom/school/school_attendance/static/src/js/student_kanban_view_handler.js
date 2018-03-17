
odoo.define('school_attendance.student_kanban_view_handler', function(require) {
"use strict";

var KanbanRecord = require('web_kanban.Record');

KanbanRecord.include({
    on_card_clicked: function() {
        if (this.model === 'school.student' && this.$el.parents('.o_school_student_attendance_kanban').length) {
                                            // needed to diffentiate : check in/out kanban view of students <-> standard student kanban view
            var action = {
                type: 'ir.actions.client',
                name: 'Confirm',
                tag: 'school_attendance_kiosk_confirm',
                student_id: this.record.id.raw_value,
                student_name: this.record.name.raw_value,
                student_state: this.record.attendance_state.raw_value,
            };
            this.do_action(action);
        } else {
            this._super.apply(this, arguments);
        }
    }
});

});
