odoo.define('sales_team.dashboard', function (require) {
"use strict";

/**
 * This file defines the Sales Team Dashboard view (alongside its renderer,
 * model and controller), extending the Kanban view.
 * The Sales Team Dashboard view is registered to the view registry.
 * A large part of this code should be extracted in an AbstractDashboard
 * widget in web, to avoid code duplication (see HelpdeskDashboard).
 */

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

var SalesTeamDashboardRenderer = KanbanRenderer.extend({
    events: _.extend({}, KanbanRenderer.prototype.events, {
        'click .o_dashboard_action': '_onDashboardActionClicked',
        'click .o_target_to_set': '_onDashboardTargetClicked',
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
            var sales_team_dashboard = QWeb.render('sales_team.SalesDashboard', {
                widget: self,
                show_demo: values && values.nb_opportunities === 0,
                values: values,
            });
            self.$el.prepend(sales_team_dashboard);
        });
    },
    /**
     * Called from the template to format the monetary value.
     *
     * @todo: use field_utils.format.monetary
     * @private
     * @returns {string} formatted value
     */
    _renderMonetaryField: function (value, currency_id) {
        var currency = session.get_currency(currency_id);
        var digits_precision = currency && currency.digits;
        value = field_utils.format.float(value || 0, {digits: digits_precision});
        if (currency) {
            if (currency.position === "after") {
                value += currency.symbol;
            } else {
                value = currency.symbol + value;
            }
        }
        return value;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent}
     */
    _onDashboardActionClicked: function (e) {
        e.preventDefault();
        var $action = $(e.currentTarget);
        this.trigger_up('dashboard_open_action', {
            action_name: $action.attr('name'),
            action_context: $action.data('context'),
        });
    },
    /**
     * @private
     * @param {MouseEvent}
     */
    _onDashboardTargetClicked: function (e) {
        if (!this.show_demo) {
            // The user is not allowed to modify the targets in demo mode
            var self = this;
            var $target = $(e.currentTarget);
            var target_name = $target.attr('name');
            var target_value = $target.attr('value');

            var $input = $('<input/>', {type: "text", name: target_name});
            if (target_value) {
                $input.attr('value', target_value);
            }
            $input.on('keyup input', function (e) {
                if(e.which === $.ui.keyCode.ENTER) {
                    self._notifyTargetChange(target_name, $input.val());
                }
            });
            $input.on('blur', function () {
                self._notifyTargetChange(target_name, $input.val());
            });

            $input.replaceAll($target)
                  .focus()
                  .select();
        }
    },
});

var SalesTeamDashboardModel = KanbanModel.extend({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

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
        return $.when();
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
            var dataPoint = self.localData[id];
            dataPoint.dashboardValues = dashboardValues;
            return id;
        });
    },
});

var SalesTeamDashboardController = KanbanController.extend({
    custom_events: _.extend({}, KanbanController.prototype.custom_events, {
        dashboard_open_action: '_onDashboardOpenAction',
        dashboard_edit_target: '_onDashboardEditTarget',
    }),

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} e
     */
    _onDashboardEditTarget: function (e) {
        var target_name = e.data.target_name;
        var target_value = e.data.target_value;
        if(isNaN(target_value)) {
            this.do_warn(_t("Wrong value entered!"), _t("Only Integer Value should be valid."));
        } else {
            var args = [target_name, parseInt(target_value)];
            this.performModelRPC('crm.lead', 'modify_target_sales_dashboard', args)
                .then(this.reload.bind(this));
        }
    },

    /**
     * @private
     * @param {OdooEvent} e
     */
    _onDashboardOpenAction: function (e) {
        var action_name = e.data.action_name;
        var action_context = e.data.action_context;
        this.do_action(action_name, {
            additional_context: action_context,
        });
    },

});

var SalesTeamDashboardView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Model: SalesTeamDashboardModel,
        Renderer: SalesTeamDashboardRenderer,
        Controller: SalesTeamDashboardController,
    }),
    display_name: _lt('Dashboard'),
    icon: 'fa-dashboard',
    searchview_hidden: true,
});

view_registry.add('sales_team_dashboard', SalesTeamDashboardView);

return {
    Model: SalesTeamDashboardModel,
    Renderer: SalesTeamDashboardRenderer,
    Controller: SalesTeamDashboardController,
};

});
