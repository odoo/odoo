odoo.define('iap.Dashboard', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var Dashboard = require('web_settings_dashboard');

var _t = core._t;
var QWeb = core.qweb;

Dashboard.Dashboard.include({
    /**
     * @override
     */
    load_apps: function (data) {
        var _super = this._super.bind(this);
        return ajax.jsonRpc('/web/dataset/call_kw', 'call', {
            model:  'iap.account',
            method: 'get_account_url',
            args: [],
            kwargs: {},
        }).then(function (url) {
            data.apps.url = url;
            return _super(data);
        });
    },
});

});
