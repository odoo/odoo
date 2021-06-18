odoo.define('hr.employee_chat', function (require) {
'use strict';
    var viewRegistry = require('web.view_registry');

    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var FormRenderer = require('web.FormRenderer');

    var KanbanController = require('web.KanbanController');
    var KanbanView = require('web.KanbanView');
    var KanbanRenderer = require('web.KanbanRenderer');
    var KanbanRecord = require('web.KanbanRecord');

    const ChatMixin = require('hr.chat_mixin');

    // USAGE OF CHAT MIXIN IN FORM VIEWS
    var EmployeeFormRenderer = FormRenderer.extend(ChatMixin);

    var EmployeeFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: FormController,
            Renderer: EmployeeFormRenderer
        }),
    });

    viewRegistry.add('hr_employee_form', EmployeeFormView);

    // USAGE OF CHAT MIXIN IN KANBAN VIEWS
    var EmployeeKanbanRecord = KanbanRecord.extend(ChatMixin);

    var EmployeeKanbanRenderer = KanbanRenderer.extend({
        config: Object.assign({}, KanbanRenderer.prototype.config, {
            KanbanRecord: EmployeeKanbanRecord,
        }),
    });

    var EmployeeKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: KanbanController,
            Renderer: EmployeeKanbanRenderer
        }),
    });

    viewRegistry.add('hr_employee_kanban', EmployeeKanbanView);
});
