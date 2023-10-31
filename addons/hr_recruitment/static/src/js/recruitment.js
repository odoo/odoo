odoo.define('job.update_kanban', function (require) {
    'use strict';
    var KanbanRecord = require('web.KanbanRecord');

    KanbanRecord.include({
        /**
         * @override
         * @private
         */
        _openRecord: function () {
            if (this.modelName === 'hr.job' && this.$(".o_hr_job_boxes a").length) {
                this.$(".o_hr_job_boxes a").first().click();
            } else {
                this._super.apply(this, arguments);
            }
        }
    });
});
