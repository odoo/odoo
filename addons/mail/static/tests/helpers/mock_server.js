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
    _mockChannelFetchPreview(args) {
        const ids = args.args[0]; // list of channel IDs to fetch preview
        const model = args.model;
        const channels = this._getRecords(model, [['id', 'in', ids]]);
        return channels.map(channel => {
            if (!channel.last_message) {
                const channelMessages = this.data['mail.message'].records.filter(
                    message => message.channel_ids.includes(channel.id)
                );
                if (channelMessages.length > 0) {
                    const lastMessageId = Math.max(...channelMessages.map(message => message.id));
                    channel.last_message = channelMessages.find(
                        message => message.id === lastMessageId
                    );
                }
            }
            return channel;
        });
    },
    /**
     * Simulate the 'channel_fold' route of of mail.channel
     * In particular sends a notification on the bus
     *
     * @private
     */
     _mockChannelFold(args) {
        const { state, uuid } = args.kwargs;
        const channel = this.data['mail.channel'].records.find(c => c.uuid === uuid);
        channel.state = state;
        // Should use something of the form session.partner_id or env.messaging.currentPartner
        // This is a limitation of the architecture of JS tests
        const notifConfirmFold = [
            ["dbName", 'res.partner', undefined],
            Object.assign({}, channel)
        ];
        this._widget.call('bus_service', 'trigger', 'notification', [notifConfirmFold]);
    },
    /**
     * Simulate the 'execute_command' route of mail.channel
     * In particular sends a notification on the bus
     *
     * @private
     */
     _mockExecuteCommand(args) {
        const [ids, commandName] = args.args;
        const channels = this.data['mail.channel'].records.filter(c => ids.includes(c.id));
        if (commandName === 'leave') {
            for (const channel of channels) {
                channel.is_pinned = false;
                // Should use something of the form session.partner_id or env.messaging.currentPartner
                // This is a limitation of the architecture of JS tests
                const notifConfirmUnpin = [
                    ["dbName", 'res.partner', undefined],
                    Object.assign({}, channel, { info: 'unsubscribe' })
                ];
                this._widget.call('bus_service', 'trigger', 'notification', [notifConfirmUnpin]);
            }
            return;
        }
        throw new Error(`mail/mock_server: the route execute_command doesn't implement the command "${commandName}"`);
    },
    /**
     * Simulate the '/mail/read_followers' route
     *
     * @private
     * @return {Object} list of followers
     */
    async _mockFollowersRead(args) {
        const ids = args.follower_ids; // list of followers IDs to read
        const followers = this._getRecords('mail.followers', [['id', 'in', ids]]);
        return { followers };
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
     * Simulate the 'get_mention_suggestions' on 'res.partner'.
     *
     * @private
     * @returns {Array[]}
     */
    _mockResPartnerGetMentionSuggestions(args) {
        const search = args.kwargs.search || '';
        const limit = args.kwargs.limit || 8;

        /**
         * Returns the given list of partners after filtering it according to
         * the logic of the Python method `get_mention_suggestions` for the
         * given search term. The result is truncated to the given limit and
         * formatted as expected by the original method.
         *
         * @param {Object[]} partners
         * @param {string} search
         * @param {integer} limit
         * @returns {Object[]}
         */
        const mentionSuggestionsFilter = function (partners, search, limit) {
            const matchingPartners = partners
                .filter(partner => {
                    // avoid inactive
                    if (partner.active === false) {
                        return false;
                    }
                    // no search term is considered as return all
                    if (!search) {
                        return true;
                    }
                    // otherwise name or email must match search term
                    if (partner.name && partner.name.includes(search)) {
                        return true;
                    }
                    if (partner.email && partner.email.includes(search)) {
                        return true;
                    }
                    return false;
                }).map(partner => {
                    // expected format
                    return {
                        email: partner.email,
                        id: partner.id,
                        name: partner.name,
                    };
                });
            // reduce results to max limit
            matchingPartners.length = Math.min(matchingPartners.length, limit);
            return matchingPartners;
        };

        // add main suggestions based on users
        const partnersFromUsers = this.data['res.users'].records
            .map(user => this.data['res.partner'].records[user.partner_id])
            .filter(partner => partner);
        const mainMatchingPartners = mentionSuggestionsFilter(partnersFromUsers, search, limit);

        let extraMatchingPartners = [];
        // if not enough results add extra suggestions based on partners
        if (mainMatchingPartners.length < limit) {
            const partners = this.data['res.partner'].records.filter(partner =>
                // avoid duplicates in extra
                !partnersFromUsers.includes(partner)
            );
            extraMatchingPartners = mentionSuggestionsFilter(partners, search, limit);
        }
        return [mainMatchingPartners, extraMatchingPartners];
    },
    /**
     * Simulate the '/mail/init_messaging' route
     *
     * @private
     * @return {Object}
     */
    _mockInitMessaging: function () {
        return _.defaults(this.initMessagingData || {}, {
            channel_slots: [],
            commands: [],
            mail_failures: [],
            mention_partner_suggestions: [],
            menu_id: false,
            needaction_inbox_counter: 0,
            partner_root: {
                active: false,
                display_name: "OdooBot",
                id: 2,
            },
            public_partner: {
                active: false,
                display_name: "Public user",
                id: 4,
            },
            shortcodes: [],
            starred_counter: 0,
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
        if (args.kwargs.limit) {
            return messages.slice(0, args.kwargs.limit);
        }
        return messages;
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
     * Simulate the 'message_post' Python method
     *
     * @private
     * @return {integer}
     */
    _mockMessagePost(args) {
        const {
            args: [res_id],
            model: res_model,
            kwargs: postData,
        } = args;
        const records = this.data['mail.message'].records;
        const messageIds = records.map(message => message.id);
        const id = Math.max(...messageIds, 0) + 1;
        const record = Object.assign({
            id,
            res_id,
            model: res_model,
        }, postData);
        records.push(record);
        return id;
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
                var metaData = [dbName, 'mail.channel', message.res_id];
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
    async _performRpc(route, args) {
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
        if (args.method === 'channel_fold') {
            return this._mockChannelFold(args);
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
        if (args.method === 'execute_command') {
            return this._mockExecuteCommand(args);
        }
        if (args.method === 'get_activity_data') {
            return Promise.resolve(this._mockGetActivityData(args));
        }
        if (args.method === 'get_mention_suggestions') {
            if (args.model === 'res.partner') {
                return this._mockResPartnerGetMentionSuggestions(args);
            }
        }
        if (args.method === 'message_fetch') {
            return Promise.resolve(this._mockMessageFetch(args));
        }
        if (args.method === 'message_format') {
            return Promise.resolve(this._mockMessageFormat(args));
        }
        if (args.method === 'message_post') {
            return Promise.resolve(this._mockMessagePost(args));
        }
        if (route === '/mail/read_followers') {
            return this._mockFollowersRead(args);
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
