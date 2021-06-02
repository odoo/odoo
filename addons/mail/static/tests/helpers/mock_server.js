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
     * Simulate the 'get_activity_method' on 'mail.activity'
     *
     * @private
     * @return {Object}
     */
    _mockGetActivityData: function (args) {
        var self = this;

        var domain = args.kwargs.domain;
        var model = args.kwargs.res_model;
        var records = this._getRecords(model, domain);

        var activityTypes = this._getRecords('mail.activity.type', []);
        var activityIds = _.pluck(records, 'activity_ids').flat();

        var groupedActivities = {};
        var resIdToDeadline = {};
        var groups = self._mockReadGroup('mail.activity', {
            domain: [['id', 'in', activityIds]],
            fields: ['res_id', 'activity_type_id', 'ids:array_agg(id)', 'date_deadline:min(date_deadline)'],
            groupby: ['res_id', 'activity_type_id'],
            lazy: false,
        });
        groups.forEach(function (group) {
            // mockReadGroup doesn't correctly return all asked fields
            var activites = self._getRecords('mail.activity', group.__domain);
            group.activity_type_id = group.activity_type_id[0];
            var minDate;
            activites.forEach(function (activity) {
                if (!minDate || moment(activity.date_deadline) < moment(minDate)) {
                    minDate = activity.date_deadline;
                }
            });
            group.date_deadline = minDate;
            resIdToDeadline[group.res_id] = minDate;
            var state;
            if (group.date_deadline === moment().format("YYYY-MM-DD")) {
                state = 'today';
            } else if (moment(group.date_deadline) > moment()) {
                state = 'planned';
            } else {
                state = 'overdue';
            }
            if (!groupedActivities[group.res_id]) {
                groupedActivities[group.res_id] = {};
            }
            groupedActivities[group.res_id][group.activity_type_id] = {
                count: group.__count,
                state: state,
                o_closest_deadline: group.date_deadline,
                ids: _.pluck(activites, 'id'),
            };
        });

        return {
            activity_types: activityTypes.map(function (type) {
                var mailTemplates = [];
                if (type.mail_template_ids) {
                    mailTemplates = type.mail_template_ids.map(function (id) {
                        var template = _.findWhere(self.data['mail.template'].records, {id: id});
                        return {
                            id: id,
                            name: template.name,
                        };
                    });
                }
                return [type.id, type.display_name, mailTemplates];
            }),
            activity_res_ids: _.sortBy(_.pluck(records, 'id'), function (id) {
                return moment(resIdToDeadline[id]);
            }),
            grouped_activities: groupedActivities,
        };
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
        var mod_channel_ids = args.kwargs.moderated_channel_ids;
        var messages = this._getRecords(model, domain);
        if (mod_channel_ids) {
            var mod_messages = this._getRecords(
                model,
                [['model', '=', 'mail.channel'],
                 ['res_id', 'in', mod_channel_ids],
                 ['need_moderation', '=', true]]
            );
            messages = _.union(messages, mod_messages);
        }
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
     * @private
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
     *
     * @private
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
     * Simulate the 'set_message_done' Python method, which turns provided
     * needaction message to non-needaction (i.e. they are marked as read from
     * from the Inbox mailbox). Also notify on the longpoll bus that the
     * messages have been marked as read, so that UI is updated.
     *
     * @private
     * @param {Object} args
     */
    _mockSetMessageDone: function (args) {
        var self = this;
        var messageIDs = args.args[0];
        _.each(messageIDs, function (messageID) {
            var message = _.findWhere(self.data['mail.message'].records, {
                id: messageID
            });
            if (message) {
                message.needaction = false;
                message.needaction_partner_ids = [];
            }
        });
        var header = [null, 'res.partner'];
        var data = { type: 'mark_as_read', message_ids: messageIDs };
        var notifications = [[header, data]];
        this._widget.call('bus_service', 'trigger', 'notification', notifications);
    },
    /**
     * @override
     */
    _performRpc: function (route, args) {
        // routes
        if (route === '/mail/init_messaging') {
            return Promise.resolve(this._mockInitMessaging(args));
        }
        // methods
        if (args.method === 'channel_fetch_listeners') {
            return Promise.resolve([]);
        }
        if (args.method === 'channel_fetch_preview') {
            return Promise.resolve(this._mockChannelFetchPreview(args));
        }
        if (args.method === 'channel_minimize') {
            return Promise.resolve();
        }
        if (args.method === 'channel_seen') {
            return Promise.resolve();
        }
        if (args.method === 'channel_fetched') {
            return Promise.resolve();
        }
        if (args.method === 'get_activity_data') {
            return Promise.resolve(this._mockGetActivityData(args));
        }
        if (args.method === 'message_fetch') {
            return Promise.resolve(this._mockMessageFetch(args));
        }
        if (args.method === 'message_format') {
            return Promise.resolve(this._mockMessageFormat(args));
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
            return Promise.resolve(res);
        }
        if (args.method === 'set_message_done') {
            return Promise.resolve(this._mockSetMessageDone(args));
        }
        if (args.method === 'moderate') {
            return Promise.resolve(this._mockModerate(args));
        }
        if (args.method === 'notify_typing') {
            return Promise.resolve();
        }
        if (args.method === 'set_message_done') {
            return Promise.resolve();
        }
        return this._super(route, args);
    },
});

});
