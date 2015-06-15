odoo.define('project.update_kanban', function (require) {

var KanbanRecord = require('web_kanban.Record');
var KanbanView = require('web_kanban.KanbanView');
var data = require('web.data');
var session = require('web.session');


KanbanRecord.include({
    on_card_clicked: function() {
        if (this.model === 'project.project') {
            this.$('.o_project_kanban_boxes a').first().click();
        } else {
            this._super.apply(this, arguments);
        }
    },
});
});
