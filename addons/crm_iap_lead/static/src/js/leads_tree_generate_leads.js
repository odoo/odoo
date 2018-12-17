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
            this.$buttons.on('click', '.o_button_generate_leads', function () {
                self._rpc({
                    model: 'ir.model.data',
                    method: 'xmlid_to_res_id',
                    kwargs: {xmlid: 'crm.crm_generate_leads_form'},
                }).then(function (res_id) {
                    self.do_action({
                        type: 'ir.actions.act_window',
                        res_model: 'crm.iap.lead.request',
                        target: 'new',
                        views: [[res_id, 'form']],
                    });
                });
            });
        }
    }

    var RequestListController = ListController.extend({
        buttons_template: 'RequestListView.buttons',
        /**
         * Extends the renderButtons function of ListView by adding an event listener
         * on the generate leads button.
         *
         * @override
         */
        renderButtons: function () {
            this._super.apply(this, arguments); // Possibly sets this.$buttons
            renderGenerateLeadsButton.apply(this, arguments);
        }
    });

    var RequestListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: RequestListController,
        }),
    });

    var RequestKanbanController = KanbanController.extend({
        /**
         * Extends the renderButtons function of KanbanView by adding an event listener
         * on the generate leads button.
         *
         * @override
         */
        renderButtons: function () {
            this._super.apply(this, arguments); // Possibly sets this.$buttons
            renderGenerateLeadsButton.apply(this, arguments);
        }
    });

    var RequestKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: RequestKanbanController,
        }),
    });

    viewRegistry.add('crm_iap_lead_request_tree', RequestListView);
    viewRegistry.add('crm_iap_lead_request_kanban', RequestKanbanView);
});
