odoo.define('account_accountant.dashboard', function (require) {
"use strict";

var core = require('web.core');
var field_utils = require('web.field_utils');
var KanbanView = require('web.KanbanView');
var KanbanModel = require('web.KanbanModel');
var KanbanRenderer = require('web.KanbanRenderer');
var KanbanController = require('web.KanbanController');
var session = require('web.session');
var view_registry = require('web.view_registry');

var QWeb = core.qweb;
var _t = core._t;
var _lt = core._lt;

const COMPANY_METHOD_TYPE = "company_object";

var AccountDashboardRenderer = KanbanRenderer.extend({
    events: _.extend({}, KanbanRenderer.prototype.events, {
        'click .account_accountant_dashboard_action': 'onDashboardActionClicked',
    }),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Notifies the controller that the target has changed.
     *
     * @private
     * @param {string} target_name the name of the changed target
     * @param {string} value the new value
     */
    _notifyTargetChange: function (target_name, value) {
        this.trigger_up('dashboard_edit_target', {
            target_name: target_name,
            target_value: value,
        });
    },
  /**
     * @override
     * @private
     * @returns {Deferred}
     */
    _render: function () {
        var self = this;

        return this._super.apply(this, arguments).then(function () {
            var values = self.state.dashboardValues;
            var account_dashboard = QWeb.render('account_accountant.AccountDashboard', {
                widget: self,
                values: values,
            });
            self.$el.prepend(account_dashboard);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent}
     */
    onDashboardActionClicked: function(e) {
        /* This functions allows the buttons of the setup bar to trigger Python
        * code defined in api.model functions, in res.company, and then to execute
        * the action returned by those.
        * It uses the 'type' attributes on buttons : if 'company_object', it will
        * run Python function 'name' of company, otherwise, it will directly execute
        * the action matching 'name'.
        */
        e.preventDefault();
        var self = this;
        var $action = $(e.currentTarget);
        var name_attr = $action.attr('name');
        var type_attr = $action.attr('type');
        var action_context = $action.data('context');

        if(type_attr == COMPANY_METHOD_TYPE) {
           this._rpc({
                    model: 'res.company',
                    method: name_attr,
                    args: [],
                })
                .then(
                    function(rslt_action) {
                        self.do_action(rslt_action, {
                            action_context: action_context,
                        })
                    });
        }
        else { //By default, we consider the content of 'name' as an action.
            self.do_action(name_attr, {
                action_context: action_context,
            });
        }
    },
});

var AccountDashboardModel = KanbanModel.extend({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    init: function () {
        this.dashboardValues = {};
        this._super.apply(this, arguments);
    },

    /**
     * @override
     */
    get: function (localID) {
        var result = this._super.apply(this, arguments);
        if (this.dashboardValues[localID]) {
            result.dashboardValues = this.dashboardValues[localID];
        }
        return result;
    },


    /**
     * @œverride
     * @returns {Deferred}
     */
    load: function () {
        return this._loadDashboard(this._super.apply(this, arguments));
    },
    /**
     * @œverride
     * @returns {Deferred}
     */
    reload: function () {
        return this._loadDashboard(this._super.apply(this, arguments));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @abstract
     * @returns {Deferred -> Object} resolves to the required dashboard data
     */
    _fetchDashboardData: function () {
        return $.when(this._rpc({
                    model: 'account.journal',
                    method: 'retrieve_account_dashboard',
                    args: [],
                }));
    },
    /**
     * @private
     * @param {Deferred} super_def a deferred that resolves with a dataPoint id
     * @returns {Deferred -> string} resolves to the dataPoint id
     */
    _loadDashboard: function (super_def) {
        var self = this;
        var dashboard_def = this._fetchDashboardData();
        return $.when(super_def, dashboard_def).then(function (id, dashboardValues) {
            self.dashboardValues[id] = dashboardValues;
            return id;
        });
    },
});

var AccountDashboardController = KanbanController.extend({
    custom_events: _.extend({}, KanbanController.prototype.custom_events, {
        dashboard_open_action: '_onDashboardOpenAction',
    }),

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} e
     */
    _onDashboardOpenAction: function (e) {
        var action_name = e.data.action_name;
        var action_context = e.data.action_context;
        return this.do_action(action_name, {
            additional_context: action_context,
        });
    },
});

var AccountDashboardView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Model: AccountDashboardModel,
        Renderer: AccountDashboardRenderer,
        Controller: AccountDashboardController,
    }),
    display_name: _lt('Dashboard'),
    icon: 'fa-dashboard',
    searchview_hidden: true,
});

view_registry.add('account_accountant_dashboard', AccountDashboardView);

return {
    Model: AccountDashboardModel,
    Renderer: AccountDashboardRenderer,
    Controller: AccountDashboardController,
};

});