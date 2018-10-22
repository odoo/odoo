odoo.define('iap.Dashboard', function (require) {
"use strict";

var Dashboard = require('web_settings_dashboard');

Dashboard.Dashboard.include({
    /**
     * @override
     */
    load_apps: function (data) {
        var _super = this._super.bind(this);
        return this._rpc({
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
