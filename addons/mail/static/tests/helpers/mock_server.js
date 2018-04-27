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
     * Simulate the '/mail.channel/channel_fetch_preview' route
     *
     * @private
     * @return {$.Promise<Object[]>} resolved with list of channels previews
     */
    _mockChannelFetchPreview: function (args) {
        var self = this;
        var ids = args.args[0]; // list of channel ids to fetch preview
        var model = args.model;
        var channels = this._getRecords(model, [['id', 'in', ids]]);
        var previews = _.map(channels, function (channel) {
            var maxMessageID = _.max(channel.channel_message_ids);
            var lastMessage = self._getRecords('mail.message', [['id', '=', maxMessageID]])[0];
            channel.last_message = lastMessage;
            return channel;
        });
        return $.when(previews);
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
            'mail_failures': [],
        });
    },

    /**
     * Simulate the 'message_fetch' Python method
     *
     * @return {Object}
     */
    _mockMessageFetch: function (args) {
        var domain = args.args[0];
        var model = args.model;
        var messages = this._getRecords(model, domain);
        // sorted from highest ID to lowest ID (i.e. from youngest to oldest)
        messages.sort(function (m1, m2) {
            return m1.id < m2.id ? 1 : -1;
        });
        // pick at most 'limit' messages
        return $.when(messages.slice(0, args.kwargs.limit));
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
        if (args.method === 'channel_fetch_preview') {
            return this._mockChannelFetchPreview(args);
        }
        return this._super(route, args);
    },
});

});
