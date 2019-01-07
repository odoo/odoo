odoo.define('web.planner', function (require) {
"use strict";

var core = require('web.core');
var SystrayMenu = require('web.SystrayMenu');
var planner = require('web.planner.common');
var session = require('web.session');

var PlannerLauncher = planner.PlannerLauncher.extend({
    start: function() {
        core.bus.on("change_menu_section", this, this.on_menu_clicked);
        return $.when(this._super.apply(this, arguments), this._loadPlannerDef);
    },
    _fetch_planner_data: function () {
        var planner_by_menu = this.planner_by_menu = {};
        return this._rpc({
                model: 'web.planner',
                method: 'search_read',
                kwargs: {context: session.user_context},
            })
            .then(function (records) {
                _.each(records, function (planner) {
                    planner.data = $.parseJSON(planner.data) || {};
                    planner_by_menu[planner.menu_id[0]] = planner;
                });
            });
    },
    on_menu_clicked: function (menu_id) {
        if (this.planner_by_menu[menu_id]) {
            this._setup_for_planner(this.planner_by_menu[menu_id]);
        } else {
            this.do_hide();
        }
    },
    _update_parent_progress_bar: function (percent) {
        this._super.apply(this, arguments);
        this.do_show();
    },
});

if (session.is_system) {
    SystrayMenu.Items.push(PlannerLauncher);
}

return {
    PlannerLauncher: PlannerLauncher,
};

});
