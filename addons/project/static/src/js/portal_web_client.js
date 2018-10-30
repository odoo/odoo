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

        /**
         * Call the 'service', using data from the 'event' that
         * has triggered the service call.
         *
         * For the ajax service, the arguments are extended with
         * the target so that it can call back the caller.
         *
         * @override
         * @param  {OdooEvent} event
         */
        _call_service: function (ev) {
            var self = this;
            if (ev.data.service === 'ajax' &&
                ev.data.method === 'rpc' &&
                ev.data.args[0] === '/mail/init_messaging') {
                var args = arguments;
                ev.data.callback($.when(this._waitHijackRPCs.then(function () {
                    var event = args[0];
                    var rpc = require('web.rpc');
                    var query = rpc.buildQuery({
                        args: [],
                        context: event.data.args[1]['context'],
                        route: event.data.args[0],
                        params: event.data.args[1],
                    });
                    event.data.args[0] = query.route;
                    event.data.args[1] = query.params;

                    var eventArgs = event.data.args.concat(event.target);
                    var service = self.services[event.data.service];
                    return service[event.data.method].apply(service, eventArgs);
                })));
            } else {
                this._super.apply(this, arguments);
            }
        },

        _onHijackRPCs: function (ev) {
            this._waitHijackRPCs.resolve();
        },
    });

    return new ProjectWebClient();
});
