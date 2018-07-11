odoo.define('project.portal_kanban_model', function (require) {

var KanbanModel = require('web.KanbanModel');

/**
 * Intercepts the ID of the task being edited if there is one, so as to use it in _hijackRpcs
 */
KanbanModel.include({
    save: function (recordID, options) {
        var record = this.localData[recordID];
        var currentlyEditedTask = record['model'] === 'project.task' ? record['res_id'] : false;
        this.trigger_up('saveKanbanTask', {taskId: currentlyEditedTask});
        return this._super.apply(this, arguments);
    },
});
});
