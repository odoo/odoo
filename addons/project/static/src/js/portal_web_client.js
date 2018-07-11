/**
 * The purpose of this file is to inject a "backend view" into the portal.
 * Everything that requires direct access to the DOM and/or should be executed
 * on load is defined here.
 */

odoo.define('web.web_client', function (require) {
    var WebClient = require('web.WebClient');

    /**
     * The webclient fires an RPC to /mail/init_messaging upon
     * initialization. We need to delay that call until PortalWebclientView
     * redirects RPC's to a public route with token check in case
     * the user is not logged in.
     * This override serves the purpose of creating that delay.
     */
    var ProjectWebClient = WebClient.extend({
        custom_events: _.extend({}, WebClient.prototype.custom_events, {
            hijackRPCs: '_onHijackRPCs',
        }),
        init: function () {
            this._waitHijackRPCs = $.Deferred();
            this._super.apply(this, arguments);
        },

        _call_service: function (ev) {
            if (ev.data.service === 'ajax' &&
                ev.data.method === 'rpc' &&
                ev.data.args[0] === '/mail/init_messaging') {
                var args = arguments;
                this._waitHijackRPCs.then(function () {
                    this._super.apply(this, args);
                }.bind(this));
                return;
            };
            return this._super.apply(this, arguments);
        },

        _onHijackRPCs: function (ev) {
            this._waitHijackRPCs.resolve();
        },
    });

    return new ProjectWebClient();
});
