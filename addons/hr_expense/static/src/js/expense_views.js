odoo.define('hr_expense.expenses.tree', function (require) {
"use strict";
    var DocumentUploadMixin = require('hr_expense.documents.upload.mixin');
    var KanbanController = require('web.KanbanController');
    var KanbanView = require('web.KanbanView');
    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');
    var core = require('web.core');
    var ListRenderer = require('web.ListRenderer');
    var session = require('web.session');

    var QWeb = core.qweb;

    var ExpensesListController = ListController.extend(DocumentUploadMixin, {
        buttons_template: 'ExpensesListView.buttons',
        events: _.extend({}, ListController.prototype.events, {
            'click .o_button_upload_expense': '_onUpload',
            'change .o_expense_documents_upload .o_form_binary_form': '_onAddAttachment',
        }),
    });

    var ExpenseListRenderer = ListRenderer.extend({
        _render: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                return self._rpc({
                    model: 'hr.expense',
                    method: 'get_expense_dashbord',
                    context: self.context,
                });
            }).then(function (result) {
                self.$el.parent().find('.o_expense_container').remove();
                var elem = QWeb.render('hr_expense.dashboard_list_header', {
                    expenses: result,
                    render_monetary_field: self.render_monetary_field,
                });
                self.$el.before(elem);
            });
        },
        render_monetary_field: function (value, currency_id) {
            value = value.toFixed(2);
            var currency = session.get_currency(currency_id);
            if (currency) {
                if (currency.position === "after") {
                    value += currency.symbol;
                } else {
                    value = currency.symbol + value;
                }
            }
            return value;
        }
    });

    var ExpensesListViewDashboardUpload = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Renderer: ExpenseListRenderer,
            Controller: ExpensesListController,
        }),
    });

    var ExpensesListViewDashboard = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Renderer: ExpenseListRenderer,
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

    viewRegistry.add('hr_expense_tree_dashboard_upload', ExpensesListViewDashboardUpload);
    viewRegistry.add('hr_expense_tree_dashboard', ExpensesListViewDashboard);
    viewRegistry.add('hr_expense_kanban', ExpensesKanbanView);
});
