odoo.define('web.DashboardMixins', function (require) {
"use strict";

/**
 * The Dashboard Mixins are designed to be used by views requiring an extra
 * dashboard. They are 4 mixins, one for each part of the view's subclasses
 * (Renderer, Model and Controller) and one for the actual view.
 *
 * In Odoo, dashboards are generally used to display user-related data, above 
 * the actual view.
 *
 * For a guide on how to use these mixins, please refer to the examples of
 * hr_holidays_dashboard.js or sales_team_dashboard.js.
 */

var BasicModel = require('web.BasicModel');
var core = require('web.core');

var _lt = core._lt;

var DashboardRendererMixin = {
    events: {
        'click .o_dashboard_action': '_onDashboardActionClicked',
        'click .o_target_to_set': '_onDashboardTargetClicked',
    },

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
        var self = this;
        var $target = $(e.currentTarget);
        var target_name = $target.attr('name');
        var target_value = $target.attr('value');

        var $input = $('<input/>', {type: "text", name: target_name});
        if (target_value) {
            $input.attr('value', target_value);
        }
        $input.on('keyup input', function (e) {
            if (e.which === $.ui.keyCode.ENTER) {
                self._notifyTargetChange(target_name, $input.val());
            }
        });
        $input.on('blur', function () {
            self._notifyTargetChange(target_name, $input.val());
        });
        $input.replaceAll($target)
              .focus()
              .select();
    },
};

var DashboardModelMixin = {
    /**
     * Complementary method. To call from the Model widget's init method.
     */
    init: function () {
        this.dashboardValues = {};
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Complementary method. To call from the Model widget's get method.
     *
     * @returns {Object}
     */
    get: function (localID, result) {
        if (this.dashboardValues[localID]) {
            result = result || {};
            result.dashboardValues = this.dashboardValues[localID];
        }
        return result;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Make rpc call to fetch dashboard data.
     *
     * @abstract
     * @private
     * @returns {Deferred -> Object} resolves to the required dashboard data
     */
    _fetchDashboardData: function () {
        return $.when();
    },
    /**
     * To call from load & reload methods.
     * 
     * @private
     * @param {Deferred} super_def a deferred that resolves with a dataPoint id
     * @returns {Deferred<string>} resolves to the dataPoint id
     */
    _loadDashboard: function (super_def) {
        var self = this;
        var dashboard_def = this._fetchDashboardData();
        return $.when(super_def, dashboard_def).then(function(id, dashboardValues) {
            self.dashboardValues[id] = dashboardValues;
            return id;
        });
    },
};

var DashboardControllerMixin = {
    custom_events: {
        dashboard_edit_target: '_onDashboardEditTarget',
        dashboard_open_action: '_onDashboardOpenAction',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handle the edition of the target, most likely save it with an rpc call.
     *
     * @abstract
     * @private
     * @param {OdooEvent} e
     */
    _onDashboardEditTarget: function (e) {},
    /**
     * @private
     * @param {OdooEvent} e
     */
    _onDashboardOpenAction: function (e) {
        var action_name = e.data.action_name;
        var action_context = e.data.action_context;
        return this.do_action(
            action_name,
            {additional_context: action_context}
        );
    },
};

var DashboardViewMixin = {
    display_name: _lt('Dashboard'),
    icon: 'fa-dashboard',
    searchview_hidden: true,
};

return {
    Controller: DashboardControllerMixin,
    Model: DashboardModelMixin,
    Renderer: DashboardRendererMixin,
    View: DashboardViewMixin,
};
});
