odoo.define('website.planner', function (require) {
'use strict';

var session = require('web.session');
var planner = require('web.planner.common');
var Widget = require('web.Widget');
var websiteNavbarData = require('website.navbar');

if (!session.is_system) {
    return;
}

var WebsitePlannerLauncher = planner.PlannerLauncher.extend({
    /**
     * @override
     */
    _fetch_planner_data: function () {
        var self = this;
        return this._rpc({
            model: 'web.planner',
            method: 'search_read',
            args: [[['planner_application', '=', 'planner_website']]],
        }).then(function (planner) {
            if (!planner.length) return;

            planner[0].data = $.parseJSON(planner[0].data) || {};
            self._setup_for_planner(planner[0]);
        });
    },
});

var PlannerMenu = Widget.extend({
    xmlDependencies: ['/web_planner/static/src/xml/web_planner.xml'],
    
    /**
     * Instantiates the planner launcher and adds it to the DOM.
     *
     * @override
     */
    start: function () {
        var websitePlannerLauncher = new WebsitePlannerLauncher(this);
        return $.when(
            this._super.apply(this, arguments),
            websitePlannerLauncher.prependTo(this.$el)
        );
    },
});

websiteNavbarData.websiteNavbarRegistry.add(PlannerMenu, '.o_menu_systray');

return WebsitePlannerLauncher;
});
