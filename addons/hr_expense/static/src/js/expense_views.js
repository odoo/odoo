odoo.define('hr_expense.expenses.tree', function (require) {
"use strict";
    var DocumentUploadMixin = require('hr_expense.documents.upload.mixin');
    var KanbanController = require('web.KanbanController');
    var KanbanView = require('web.KanbanView');
    var PivotView = require('web.PivotView');
    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');
    var core = require('web.core');
    var ListRenderer = require('web.ListRenderer');
    var KanbanRenderer = require('web.KanbanRenderer');
    var PivotRenderer = require('web.PivotRenderer');
    var session = require('web.session');
    const config = require('web.config');

    var QWeb = core.qweb;

    var ExpensesListController = ListController.extend(DocumentUploadMixin, {
        buttons_template: 'ExpensesListView.buttons',
        events: _.extend({}, ListController.prototype.events, {
            'click .o_button_upload_expense': '_onUpload',
            'change .o_expense_documents_upload .o_form_binary_form': '_onAddAttachment',
        }),
    });

    const ExpenseQRCodeMixin = {
        async _renderView() {
            const self = this;
            await this._super(...arguments);
            const google_url = "https://play.google.com/store/apps/details?id=com.odoo.mobile";
            const apple_url = "https://apps.apple.com/be/app/odoo/id1272543640";
            const action_desktop = {
                name: 'Download our App',
                type: 'ir.actions.client',
                tag: 'expense_qr_code_modal',
                params: {'url': "https://apps.apple.com/be/app/odoo/id1272543640"},
                target: 'new',
            };
            this.$el.find('img.o_expense_apple_store').on('click', function(event) {
                event.preventDefault();
                if (!config.device.isMobile) {
                    self.do_action(_.extend(action_desktop, {params: {'url': apple_url}}));
                } else {
                    self.do_action({type: 'ir.actions.act_url', url: apple_url});
                }
            });
            this.$el.find('img.o_expense_google_store').on('click', function(event) {
                event.preventDefault();
                if (!config.device.isMobile) {
                    self.do_action(_.extend(action_desktop, {params: {'url': google_url}}));
                } else {
                    self.do_action({type: 'ir.actions.act_url', url: google_url});
                }
            });
        },
    };

    const ExpenseDashboardMixin = {
        _render: async function () {
            var self = this;
            await this._super(...arguments);
            const result = await this._rpc({
                model: 'hr.expense',
                method: 'get_expense_dashboard',
                context: this.context,
            });

            self.$el.parent().find('.o_expense_container').remove();
            const elem = QWeb.render('hr_expense.dashboard_list_header', {
                expenses: result,
                render_monetary_field: self.render_monetary_field,
            });
            self.$el.before(elem);
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
    };

    var ExpenseListRenderer = ListRenderer.extend(ExpenseDashboardMixin, ExpenseQRCodeMixin);

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

    var ExpenseKanbanRenderer = KanbanRenderer.extend(ExpenseDashboardMixin, ExpenseQRCodeMixin);

    var ExpensesKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: ExpensesKanbanController,
            Renderer: ExpenseKanbanRenderer,
        }),
    });

    viewRegistry.add('hr_expense_tree_dashboard_upload', ExpensesListViewDashboardUpload);
    viewRegistry.add('hr_expense_tree_dashboard', ExpensesListViewDashboard);
    viewRegistry.add('hr_expense_kanban', ExpensesKanbanView);
});
