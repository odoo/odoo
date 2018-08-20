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
     * @param {Object} [data.initMessaging] init messaging data
     * @param {Object} [options.services] list of extra services to load for
     *   the tests (e.g. MailService or BusService)
     * @param {Widget} [options.widget] mocked widget (use to call services)
     */
    init: function (data, options) {
        if (data && data.initMessaging) {
            this.initMessagingData = data.initMessaging;
            delete data.initMessaging;
        }
        this._widget = options.widget;

        this._super.apply(this, arguments);
    },

    /**
     * Simulate the '/mail.channel/channel_fetch_preview' route
     *
     * @private
     * @return {Object[]} list of channels previews
     */
    _mockChannelFetchPreview: function (args) {
        var self = this;
        var ids = args.args[0]; // list of channel IDs to fetch preview
        var model = args.model;
        var channels = this._getRecords(model, [['id', 'in', ids]]);
        var previews = _.map(channels, function (channel) {
            var channelMessages = _.filter(self.data['mail.message'].records, function (message) {
                return _.contains(message.channel_ids, channel.id);
            });
            var lastMessage = _.max(channelMessages, function (message) {
                return message.id;
            });
            channel.last_message = lastMessage;
            return channel;
        });
        return previews;
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
     * @private
     * @return {Object[]}
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
        return messages.slice(0, args.kwargs.limit);
    },
    /**
     * Simulate the 'message_format' Python method
     *
     * @return {Object[]}
     */
    _mockMessageFormat: function (args) {
        var messageIDs = args.args[0];
        var domain = [['id', 'in', messageIDs]];
        var model = args.model;
        var messages = this._getRecords(model, domain);
        // sorted from highest ID to lowest ID (i.e. from youngest to oldest)
        messages.sort(function (m1, m2) {
            return m1.id < m2.id ? 1 : -1;
        });
        return messages;
    },
    /**
     * Simulate the 'moderate' Python method
     */
    _mockModerate: function (args) {
        var messageIDs = args.args[0];
        var decision = args.args[1];
        var model = this.data['mail.message'];
        if (decision === 'reject' || decision === 'discard') {
            model.records = _.reject(model.records, function (rec) {
                return _.contains(messageIDs, rec.id);
            });
            // simulate notification back (deletion of rejected/discarded
            // message in channel)
            var dbName = undefined; // useless for tests
            var notifData = {
                message_ids: messageIDs,
                type: "deletion",
            };
            var metaData = [dbName, 'res.partner'];
            var notification = [metaData, notifData];
            this._widget.call('bus_service', 'trigger', 'notification', [notification]);
        } else if (decision === 'accept') {
            // simulate notification back (new accepted message in channel)
            var messages = _.filter(model.records, function (rec) {
                return _.contains(messageIDs, rec.id);
            });

            var notifications = [];
            _.each(messages, function (message) {
                var dbName = undefined; // useless for tests
                var messageData = message;
                message.moderation_status = 'accepted';
                var metaData = [dbName, 'mail.channel'];
                var notification = [metaData, messageData];
                notifications.push(notification);
            });
            this._widget.call('bus_service', 'trigger', 'notification', notifications);
        }
    },
    /**
     * @override
     */
    _performRpc: function (route, args) {
        // routes
        if (route === '/mail/init_messaging') {
            return $.when(this._mockInitMessaging(args));
        }
        // methods
        if (args.method === 'channel_fetch_listeners') {
            return $.when([]);
        }
        if (args.method === 'channel_fetch_preview') {
            return $.when(this._mockChannelFetchPreview(args));
        }
        if (args.method === 'channel_minimize') {
            return $.when();
        }
        if (args.method === 'channel_seen') {
            return $.when();
        }
        if (args.method === 'message_fetch') {
            return $.when(this._mockMessageFetch(args));
        }
        if (args.method === 'message_format') {
            return $.when(this._mockMessageFormat(args));
        }
        if (args.method === 'activity_format') {
            var res = this._mockRead(args.model, args.args, args.kwargs);
            res = res.map(function(record) {
                if (record.mail_template_ids) {
                    record.mail_template_ids = record.mail_template_ids.map(function(template_id) {
                        return {id:template_id, name:"template"+template_id};
                    });
                }
                return record;
            });
            return $.when(res);
        }
        if (args.method === 'set_message_done') {
            return $.when();
        }
        if (args.method === 'moderate') {
            return $.when(this._mockModerate(args));
        }
        if (args.method === 'notify_typing') {
            return $.when();
        }
        if (args.method === 'set_message_done') {
            return $.when();
        }
        return this._super(route, args);
    },
});

});
