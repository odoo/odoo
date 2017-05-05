odoo.define('account_accountant.dashboard', function (require) {
"use strict";

var core = require('web.core');
var formats = require('web.formats');
var Model = require('web.Model');
var session = require('web.session');
var KanbanView = require('web_kanban.KanbanView');
var data = require('web.data');
var web_client = require('web.web_client');

var QWeb = core.qweb;

var _t = core._t;
var _lt = core._lt;

const COMPANY_METHOD_TYPE = "company_object";

var AccountDashboardView = KanbanView.extend({
    display_name: _lt('Dashboard'),
    icon: 'fa-dashboard',
    searchview_hidden: true,
    events: {
        'click .account_accountant_dasboard_action': 'on_dashboard_action_clicked',
    },

    fetch_data: function() {
        return new Model('account.journal')
            .call('retrieve_account_dashboard', []);
    },

    render: function() {
        var super_render = this._super;
        var self = this;

        return this.fetch_data().then(function(result){
            var account_dashboard = QWeb.render('account_accountant.AccountDashboard', {
                widget: self,
                values: result,
            });
            super_render.call(self);
            $(account_dashboard).prependTo(self.$el);
        });
    },

    on_dashboard_action_clicked: function(ev) {
        /* This functions allows the buttons of the setup bar to trigger Python
        * code defined in api.model functions, in res.company, and then to execute
        * the action returned by those.
        * It uses the 'type' attributes on buttons : if 'company_object', it will
        * run Python function 'name' of company, otherwise, it will directly execute
        * the action matching 'name'.
        */
        ev.preventDefault();
        var $action = $(ev.currentTarget);
        var name_attr = $action.attr('name');
        var type_attr = $action.attr('type');
        var action_context = $action.data('context');

        if(type_attr == COMPANY_METHOD_TYPE) {
            new Model('res.company').call(name_attr, []).then(function(rslt_action) {
                    web_client.action_manager.do_action(rslt_action, {
                        additional_context: action_context
                    });
            });
        }
        else { //By default, we consider the content of 'name' as an action.
            this.do_action(name_attr, {
                    additional_context: action_context
            });
        }
    },

});

core.view_registry.add('account_accountant_dashboard', AccountDashboardView);

return AccountDashboardView;

});
