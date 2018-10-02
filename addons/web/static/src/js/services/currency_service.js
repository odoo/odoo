odoo.define('web.CurrencyService', function (require) {
"use strict";

var AbstractService = require('web.AbstractService');
var core = require('web.core');

var CurrencyService = AbstractService.extend({
    /**
     * Refresh currencies data into the cache
     *
     * @param {number} [res_id]
     */
    reload: function (res_id) {
        // TODO: currently, update the session info but
        // when services will be accessible everywhere,
        // this will need to be rework to work without
        // session and be self sufficient
        var session = this.getSession();

        if (!res_id || !session.currencies[res_id]) {
            this._rpc({
                route: '/web/session/get_session_info'
            }).then(function (data) {
                _.extend(session.currencies, data.currencies);
                if (odoo.session_info) {
                    odoo.session_info.currencies = session.currencies;
                }
            });
        }
    },
});

core.serviceRegistry.add('currency', CurrencyService);

return CurrencyService;

});
