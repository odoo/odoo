odoo.define('project.update_kanban', function (require) {

var kanban_common = require('web_kanban.common');
var KanbanView = require('web_kanban.KanbanView');
var data = require('web.data');
var session = require('web.session');


kanban_common.KanbanRecord.include({
    on_card_clicked: function() {
        if (this.view.dataset.model === 'project.project') {
            this.$('.o_project_kanban_boxes a').first().click();
        } else {
            this._super.apply(this, arguments);
        }
    },
});
});
