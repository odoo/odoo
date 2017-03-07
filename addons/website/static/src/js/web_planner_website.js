odoo.define('web.planner.website', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var planner = require('web.planner.common');
var rpc = require('web.rpc');
var session = require('web.session');
var website = require('website.website');

var qweb = core.qweb;

var WebsitePlannerLauncher = planner.PlannerLauncher.extend({
    _fetch_planner_data: function () {
        return rpc.query({model: 'web.planner', method: 'search_read'})
            .args([[['planner_application', '=', 'planner_website']]])
            .exec({type: "ajax"})
            .then((function (planner) {
                planner = planner.records;
                if (!planner.length) return;

                planner[0].data = $.parseJSON(planner[0].data) || {};
                this._setup_for_planner(planner[0]);
            }).bind(this));
    },
});

if (session.is_system) {
    website.TopBar.include({
        start: function () {
            var websitePlannerLauncher = new WebsitePlannerLauncher();
            var def = ajax.loadXML('/web_planner/static/src/xml/web_planner.xml', qweb).then((function() {
                return websitePlannerLauncher.prependTo(this.$(".o_menu_systray"));
            }).bind(this));
            return $.when(this._super.apply(this, arguments), def);
        },
    });
}
    
});
