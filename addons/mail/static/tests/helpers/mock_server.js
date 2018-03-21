odoo.define('mail.MockServer', function (require) {
"use strict";

var MockServer = require('web.MockServer');

MockServer.include({
    /**
     * Param 'data' may have a key 'initMessaging' which contains
     * a partial overwrite of the result from mockInitMessaging.
     *
     * Note: we must delete this key, so that this is not
     * handled as a model definition.
     *
     * @override
     * @param {Object} [data.initMessaging] 
     */
    init: function (data, options) {
        if (data && data.initMessaging) {
            this.initMessagingData = data.initMessaging;
            delete data.initMessaging;
        }
        this._super.apply(this, arguments);
    },

    /**
     * Simulate the '/mail/init_messaging' route
     *
     * @private
     * @return {Object}
     */
    _mockInitMessaging: function () {
        return _.defaults(this.initMessagingData || {}, {
            'needaction_inbox_counter': 0,
            'starred_counter': 0,
            'channel_slots': [],
            'commands': [],
            'mention_partner_suggestions': [],
            'shortcodes': [],
            'menu_id': false,
        });
    },

    /**
     * Simulate the 'message_fetch' Python method
     *
     * @return {Object}
     */
    _mockMessageFetch: function (args) {
        args.kwargs.offset = Math.max(this.data['mail.message'].records.length - args.kwargs.limit, 0);

        return this._mockSearchRead('mail.message', [
            args.args[0],
            _.keys(this.data['mail.message'].fields),
        ], args.kwargs);
    },

    /**
     * @override
     */
    _performRpc: function (route, args) {
        if (route === '/mail/init_messaging') {
            return $.when(this._mockInitMessaging(args));
        }
        if (args.method === 'message_fetch') {
            return $.when(this._mockMessageFetch(args));
        }
        if (args.method === 'channel_fetch_listeners') {
            return $.when([]);
        }
        if (args.method === 'channel_seen') {
            return $.when();
        }
        return this._super(route, args);
    },
});

});
