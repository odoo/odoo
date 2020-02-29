odoo.define('crm.leads.tree', function (require) {
"use strict";
    var ListController = require('web.ListController');
    var ListView = require('web.ListView');

    var KanbanController = require('web.KanbanController');
    var KanbanView = require('web.KanbanView');

    var viewRegistry = require('web.view_registry');

    function renderGenerateLeadsButton() {
        if (this.$buttons) {
            var self = this;
            var lead_type = self.initialState.getContext()['default_type'];
            this.$buttons.on('click', '.o_button_generate_leads', function () {
                self.do_action({
                    name: 'Generate Leads',
                    type: 'ir.actions.act_window',
                    res_model: 'crm.iap.lead.mining.request',
                    target: 'new',
                    views: [[false, 'form']],
                    context: {'is_modal': true, 'default_lead_type': lead_type},
                });
            });
        }
    }

    var LeadMiningRequestListController = ListController.extend({
        willStart: function() {
            var self = this;
            var ready = this.getSession().user_has_group('sales_team.group_sale_manager')
                .then(function (is_sale_manager) {
                    if (is_sale_manager) {
                        self.buttons_template = 'LeadMiningRequestListView.buttons';
                    }
                });
            return Promise.all([this._super.apply(this, arguments), ready]);
        },
        renderButtons: function () {
            this._super.apply(this, arguments);
            renderGenerateLeadsButton.apply(this, arguments);
        }
    });

    var LeadMiningRequestListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: LeadMiningRequestListController,
        }),
    });

    var LeadMiningRequestKanbanController = KanbanController.extend({
        willStart: function() {
            var self = this;
            var ready = this.getSession().user_has_group('sales_team.group_sale_manager')
                .then(function (is_sale_manager) {
                    if (is_sale_manager) {
                        self.buttons_template = 'LeadMiningRequestKanbanView.buttons';
                    }
                });
            return Promise.all([this._super.apply(this, arguments), ready]);
        },
        renderButtons: function () {
            this._super.apply(this, arguments);
            renderGenerateLeadsButton.apply(this, arguments);
        }
    });

    var LeadMiningRequestKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: LeadMiningRequestKanbanController,
        }),
    });

    viewRegistry.add('crm_iap_lead_mining_request_tree', LeadMiningRequestListView);
    viewRegistry.add('crm_iap_lead_mining_request_kanban', LeadMiningRequestKanbanView);
});
