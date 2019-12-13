odoo.define('hr_expense.expenses.tree', function (require) {
"use strict";
    var DocumentUploadMixin = require('hr_expense.documents.upload.mixin');
    var KanbanController = require('web.KanbanController');
    var KanbanView = require('web.KanbanView');
    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');

    var ExpensesListController = ListController.extend(DocumentUploadMixin, {
        buttons_template: 'ExpensesListView.buttons',
        events: _.extend({}, ListController.prototype.events, {
            'click .o_button_upload_expense': '_onUpload',
            'change .o_expense_documents_upload .o_form_binary_form': '_onAddAttachment',
        }),
    });

    var ExpensesListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: ExpensesListController,
        }),
    });

    var ExpensesKanbanController = KanbanController.extend(DocumentUploadMixin, {
        buttons_template: 'ExpensesKanbanView.buttons',
        events: _.extend({}, KanbanController.prototype.events, {
            'click .o_button_upload_expense': '_onUpload',
            'change .o_expense_documents_upload .o_form_binary_form': '_onAddAttachment',
        }),
    });

    var ExpensesKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: ExpensesKanbanController,
        }),
    });

    viewRegistry.add('hr_expense_tree', ExpensesListView);
    viewRegistry.add('hr_expense_kanban', ExpensesKanbanView);
});
