odoo.define('iap.Dashboard', function (require) {
"use strict";

var Dashboard = require('web_settings_dashboard');
var Widget = require('web.Widget');

Dashboard.Dashboard.include({
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        return this.all_dashboards.push('iap');
    },
            
    load_iap: function (data) {
        var self = this;
        return this._rpc({
            model:  'iap.account',
            method: 'get_account_url',
            args: [],
            kwargs: {},
        }).then(function (url) {
            data.iap = {};
            data.iap.url = url;
            return new DashboardIAP(self, data.iap).replace(self.$('.o_web_settings_dashboard_iap'));
        });
    },
});

var DashboardIAP = Widget.extend({
    template: 'iap.web_settings_dashboard_iap',

    init: function(parent, data) {
        this.data = data;
        this.parent = parent;
        return this._super.apply(this, arguments);
    },

});

});
