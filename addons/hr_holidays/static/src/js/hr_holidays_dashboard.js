odoo.define('hr_holidays.dashboard', function (require) {
"use strict";

/**
 * This file defines the Leaves Dashboard view (alongside its renderer,
 * model and controller), extending the Kanban view.
 * The Leaves Dashboard view is registered to the view registry.
 */

var core = require('web.core');
var DashboardMixins = require('web.DashboardMixins');
var KanbanController = require('web.KanbanController');
var KanbanModel = require('web.KanbanModel');
var KanbanRenderer = require('web.KanbanRenderer');
var KanbanView = require('web.KanbanView');
var view_registry = require('web.view_registry');

var QWeb = core.qweb;
var _t = core._t;


var HrHolidaysDashboardRenderer = KanbanRenderer.extend(DashboardMixins.Renderer, {
    events: _.extend({}, KanbanRenderer.prototype.events,
                     DashboardMixins.Renderer.events),
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     * @returns {Deferred}
     */
    _render: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            var values = self.state.dashboardValues;
            var hr_holidays_dashboard = QWeb.render('hr_holidays.HrHolidaysDashboard', {
                data: values,
            });
            self.$el.prepend(hr_holidays_dashboard);
        });
    },
});

var HrHolidaysDashboardModel = KanbanModel.extend(DashboardMixins.Model, {
    /**
     * @override
     */
    init: function () {
        DashboardMixins.Model.init.apply(this, arguments);
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    get: function (localID) {
        var result = this._super.apply(this, arguments);
        return DashboardMixins.Model.get.call(this, localID, result);
    },
    /**
     * @override
     * @returns {Deferred}
     */
    load: function () {
        return this._loadDashboard(this._super.apply(this, arguments));
    },
    /**
     * @override
     * @returns {Deferred}
     */
    reload: function () {
        return this._loadDashboard(this._super.apply(this, arguments));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     * @param {Deferred} super_def a deferred that resolves with a dataPoint id
     * @returns {Deferred -> string} resolves to the dataPoint id
     */
    _fetchDashboardData: function() {
        return this._rpc({
            model: 'hr.department',
            method: 'retrieve_dashboard_data',
        });
    },
});

var HrHolidaysDashboardController = KanbanController.extend(DashboardMixins.Controller, {
    custom_events: _.extend({}, KanbanController.prototype.custom_events,
        DashboardMixins.Controller.custom_events),
});

var HrHolidaysDashboardView = KanbanView.extend(DashboardMixins.View, {
    config: _.extend({}, KanbanView.prototype.config, {
        Controller: HrHolidaysDashboardController,
        Model: HrHolidaysDashboardModel,
        Renderer: HrHolidaysDashboardRenderer,
    }),
});

view_registry.add('hr_holidays_dashboard', HrHolidaysDashboardView);

return {
    Controller: HrHolidaysDashboardController,
    Model: HrHolidaysDashboardModel,
    Renderer: HrHolidaysDashboardRenderer,
    View: HrHolidaysDashboardView,
};

});
