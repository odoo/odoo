/** @odoo-module **/

import { nextAnimationFrame } from '@mail/utils/test_utils';

import MockServer from 'web.MockServer';
import { datetime_to_str } from 'web.time';

MockServer.include({
    /**
     * Param 'data' may have keys for the different magic partners/users.
     *
     * Note: we must delete these keys, so that this is not
     * handled as a model definition.
     *
     * @override
     * @param {Object} [data.currentPartnerId]
     * @param {Object} [data.currentUserId]
     * @param {Object} [data.partnerRootId]
     * @param {Object} [data.publicPartnerId]
     * @param {Object} [data.publicUserId]
     * @param {Widget} [options.widget] mocked widget (use to call services)
     */
    init(data, options) {
        if (data && data.currentPartnerId) {
            this.currentPartnerId = data.currentPartnerId;
            delete data.currentPartnerId;
        }
        if (data && data.currentUserId) {
            this.currentUserId = data.currentUserId;
            delete data.currentUserId;
        }
        if (data && data.partnerRootId) {
            this.partnerRootId = data.partnerRootId;
            delete data.partnerRootId;
        }
        if (data && data.publicPartnerId) {
            this.publicPartnerId = data.publicPartnerId;
            delete data.publicPartnerId;
        }
        if (data && data.publicUserId) {
            this.publicUserId = data.publicUserId;
            delete data.publicUserId;
        }
        this._widget = options.widget;

        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _performFetch(resource, init) {
        if (resource === '/mail/attachment/upload') {
            const ufile = init.body.get('ufile');
            const is_pending = init.body.get('is_pending');
            const model = is_pending ? 'mail.compose.message' : init.body.get('thread_model');
            const id = is_pending ? 0 : parseInt(init.body.get('thread_id'));
            const attachmentId = this._mockCreate('ir.attachment', {
                // datas,
                mimetype: ufile.type,
                name: ufile.name,
                res_id: id,
                res_model: model,
            });
            const attachment = this._getRecords('ir.attachment', [['id', '=', attachmentId]])[0];
            return new window.Response(JSON.stringify({
                'filename': attachment.name,
                'id': attachment.id,
                'mimetype': attachment.mimetype,
                'size': attachment.file_size
            }));
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    async _performRpc(route, args) {
        // routes
        if (route === '/mail/message/post') {
            if (args.thread_model === 'mail.channel') {
                return this._mockMailChannelMessagePost(args.thread_id, args.post_data, args.context);
            }
            return this._mockMailThreadMessagePost(args.thread_model, [args.thread_id], args.post_data, args.context);
        }
        if (route === '/mail/attachment/delete') {
            const { attachment_id } = args;
            return this._mockRouteMailAttachmentRemove(attachment_id);
        }
        if (route === '/mail/chat_post') {
            const uuid = args.uuid;
            const message_content = args.message_content;
            const context = args.context;
            return this._mockRouteMailChatPost(uuid, message_content, context);
        }
        if (route === '/mail/get_suggested_recipients') {
            const model = args.model;
            const res_ids = args.res_ids;
            return this._mockRouteMailGetSuggestedRecipient(model, res_ids);
        }
        if (route === '/mail/init_messaging') {
            return this._mockRouteMailInitMessaging();
        }
        if (route === '/mail/load_message_failures') {
            return this._mockRouteMailLoadMessageFailures();
        }
        if (route === '/mail/history/messages') {
            const { min_id, max_id, limit } = args;
            return this._mockRouteMailMessageHistory(min_id, max_id, limit);
        }
        if (route === '/mail/inbox/messages') {
            const { min_id, max_id, limit } = args;
            return this._mockRouteMailMessageInbox(min_id, max_id, limit);
        }
        if (route === '/mail/starred/messages') {
            const { min_id, max_id, limit } = args;
            return this._mockRouteMailMessageStarredMessages(min_id, max_id, limit);
        }
        if (route === '/mail/read_followers') {
            return this._mockRouteMailReadFollowers(args);
        }
        if (route === '/mail/read_subscription_data') {
            const follower_id = args.follower_id;
            return this._mockRouteMailReadSubscriptionData(follower_id);
        }
        if (route === '/mail/thread/messages') {
            const { min_id, max_id, limit, thread_model, thread_id } = args;
            return this._mockRouteMailThreadFetchMessages(thread_model, thread_id, max_id, min_id, limit);
        }
        if (route === '/mail/channel/messages') {
            const { channel_id, min_id, max_id, limit } = args;
            return this._mockRouteMailChannelMessages(channel_id, max_id, min_id, limit);
        }
        if (new RegExp('/mail/channel/\\d+/partner/\\d+/avatar_128').test(route)) {
            return;
        }
        // mail.activity methods
        if (args.model === 'mail.activity' && args.method === 'activity_format') {
            let res = this._mockRead(args.model, args.args, args.kwargs);
            res = res.map(function (record) {
                if (record.mail_template_ids) {
                    record.mail_template_ids = record.mail_template_ids.map(function (template_id) {
                        return { id: template_id, name: "template" + template_id };
                    });
                }
                return record;
            });
            return res;
        }
        if (args.model === 'mail.activity' && args.method === 'get_activity_data') {
            const res_model = args.args[0] || args.kwargs.res_model;
            const domain = args.args[1] || args.kwargs.domain;
            return this._mockMailActivityGetActivityData(res_model, domain);
        }
        // mail.channel methods
        if (args.model === 'mail.channel' && args.method === 'action_unfollow') {
            const ids = args.args[0];
            return this._mockMailChannelActionUnfollow(ids);
        }
        if (args.model === 'mail.channel' && args.method === 'channel_fetched') {
            const ids = args.args[0];
            return this._mockMailChannelChannelFetched(ids);
        }
        if (args.model === 'mail.channel' && args.method === 'channel_fetch_listeners') {
            return [];
        }
        if (args.model === 'mail.channel' && args.method === 'channel_fetch_preview') {
            const ids = args.args[0];
            return this._mockMailChannelChannelFetchPreview(ids);
        }
        if (args.model === 'mail.channel' && args.method === 'channel_fold') {
            const uuid = args.args[0] || args.kwargs.uuid;
            const state = args.args[1] || args.kwargs.state;
            return this._mockMailChannelChannelFold(uuid, state);
        }
        if (args.model === 'mail.channel' && args.method === 'channel_get') {
            const partners_to = args.args[0] || args.kwargs.partners_to;
            const pin = args.args[1] !== undefined
                ? args.args[1]
                : args.kwargs.pin !== undefined
                    ? args.kwargs.pin
                    : undefined;
            return this._mockMailChannelChannelGet(partners_to, pin);
        }
        if (args.model === 'mail.channel' && args.method === 'channel_info') {
            const ids = args.args[0];
            return this._mockMailChannelChannelInfo(ids);
        }
        if (args.model === 'mail.channel' && args.method === 'add_members') {
            const ids = args.args[0];
            const partner_ids = args.args[1] || args.kwargs.partner_ids;
            return this._mockMailChannelAddMembers(ids, partner_ids);
        }
        if (args.model === 'mail.channel' && args.method === 'channel_pin') {
            const uuid = args.args[0] || args.kwargs.uuid;
            const pinned = args.args[1] || args.kwargs.pinned;
            return this._mockMailChannelChannelPin(uuid, pinned);
        }
        if (args.model === 'mail.channel' && args.method === 'channel_rename') {
            const ids = args.args[0];
            const name = args.args[1] || args.kwargs.name;
            return this._mockMailChannelChannelRename(ids, name);
        }
        if (route === '/mail/channel/set_last_seen_message') {
            const id = args.channel_id;
            const last_message_id = args.last_message_id;
            return this._mockMailChannel_ChannelSeen([id], last_message_id);
        }
        if (args.model === 'mail.channel' && args.method === 'channel_set_custom_name') {
            const ids = args.args[0];
            const name = args.args[1] || args.kwargs.name;
            return this._mockMailChannelChannelSetCustomName(ids, name);
        }
        if (args.model === 'mail.channel' && args.method === 'create_group') {
            const partners_to = args.args[0] || args.kwargs.partners_to;
            return this._mockMailChannelCreateGroup(partners_to);
        }
        if (args.model === 'mail.channel' && args.method === 'execute_command_leave') {
            return this._mockMailChannelExecuteCommandLeave(args);
        }
        if (args.model === 'mail.channel' && args.method === 'execute_command_who') {
            return this._mockMailChannelExecuteCommandWho(args);
        }
        if (args.model === 'mail.channel' && args.method === 'notify_typing') {
            const ids = args.args[0];
            const is_typing = args.args[1] || args.kwargs.is_typing;
            const context = args.kwargs.context;
            return this._mockMailChannelNotifyTyping(ids, is_typing, context);
        }
        if (args.model === 'mail.channel' && args.method === 'write' && 'image_128' in args.args[1]) {
            const ids = args.args[0];
            return this._mockMailChannelWriteImage128(ids[0]);
        }
        // mail.message methods
        if (args.model === 'mail.message' && args.method === 'mark_all_as_read') {
            const domain = args.args[0] || args.kwargs.domain;
            return this._mockMailMessageMarkAllAsRead(domain);
        }
        if (args.model === 'mail.message' && args.method === 'message_format') {
            const ids = args.args[0];
            return this._mockMailMessageMessageFormat(ids);
        }
        if (args.model === 'mail.message' && args.method === 'set_message_done') {
            const ids = args.args[0];
            return this._mockMailMessageSetMessageDone(ids);
        }
        if (args.model === 'mail.message' && args.method === 'toggle_message_starred') {
            const ids = args.args[0];
            return this._mockMailMessageToggleMessageStarred(ids);
        }
        if (args.model === 'mail.message' && args.method === 'unstar_all') {
            return this._mockMailMessageUnstarAll();
        }
        if (args.model === 'res.users.settings' && args.method === '_find_or_create_for_user') {
            const user_id = args.args[0][0];
            return this._mockResUsersSettings_FindOrCreateForUser(user_id);
        }
        if (args.model === 'res.users.settings' && args.method === 'set_res_users_settings') {
            const id = args.args[0][0];
            const newSettings = args.kwargs.new_settings;
            return this._mockResUsersSettingsSetResUsersSettings(id, newSettings);
        }
        // res.partner methods
        if (args.method === 'get_mention_suggestions') {
            if (args.model === 'mail.channel') {
                return this._mockMailChannelGetMentionSuggestions(args);
            }
            if (args.model === 'res.partner') {
                return this._mockResPartnerGetMentionSuggestions(args);
            }
        }
        if (args.model === 'res.partner' && args.method === 'im_search') {
            const name = args.args[0] || args.kwargs.search;
            const limit = args.args[1] || args.kwargs.limit;
            return this._mockResPartnerImSearch(name, limit);
        }
        if (args.model === 'res.partner' && args.method === 'search_for_channel_invite') {
            const search_term = args.args[0] || args.kwargs.search_term;
            const channel_id = args.args[1] || args.kwargs.channel_id;
            const limit = args.args[2] || args.kwargs.limit;
            return this._mockResPartnerSearchForChannelInvite(search_term, channel_id, limit);
        }
        // mail.thread methods (can work on any model)
        if (args.method === 'message_subscribe') {
            const ids = args.args[0];
            const partner_ids = args.args[1] || args.kwargs.partner_ids;
            const subtype_ids = args.args[2] || args.kwargs.subtype_ids;
            return this._mockMailThreadMessageSubscribe(args.model, ids, partner_ids, subtype_ids);
        }
        if (args.method === 'message_unsubscribe') {
            const ids = args.args[0];
            const partner_ids = args.args[1] || args.kwargs.partner_ids;
            return this._mockMailThreadMessageUnsubscribe(args.model, ids, partner_ids);
        }
        if (args.method === 'message_post') {
            const id = args.args[0];
            const kwargs = args.kwargs;
            const context = kwargs.context;
            delete kwargs.context;
            return this._mockMailThreadMessagePost(args.model, [id], kwargs, context);
        }
        return this._super(route, args);
    },

    //--------------------------------------------------------------------------
    // Private Mocked Routes
    //--------------------------------------------------------------------------

    /**
     * Simulates the `/mail/attachment/delete` route.
     *
     * @private
     * @param {integer} attachment_id
     */
    async _mockRouteMailAttachmentRemove(attachment_id) {
        return this._mockUnlink('ir.attachment', [[attachment_id]]);
    },

    /**
     * Simulates the `/mail/channel/messages` route.
     *
     * @private
     * @param {integer} channel_id
     * @param {integer} limit
     * @param {integer} max_id
     * @param {integer} min_id
     * @returns {Object} list of messages
     */
    async _mockRouteMailChannelMessages(channel_id, max_id = false, min_id = false, limit = 30) {
        const domain = [
            ['res_id', '=', channel_id],
            ['model', '=', 'mail.channel'],
            ['message_type', '!=', 'user_notification'],
        ];
        return this._mockMailMessage_MessageFetch(domain, max_id, min_id, limit);
    },

    /**
     * Simulates the `/mail/chat_post` route.
     *
     * @private
     * @param {string} uuid
     * @param {string} message_content
     * @param {Object} [context={}]
     * @returns {Object} one key for list of followers and one for subtypes
     */
    async _mockRouteMailChatPost(uuid, message_content, context = {}) {
        const mailChannel = this._getRecords('mail.channel', [['uuid', '=', uuid]])[0];
        if (!mailChannel) {
            return false;
        }

        let user_id;
        // find the author from the user session
        if ('mockedUserId' in context) {
            // can be falsy to simulate not being logged in
            user_id = context.mockedUserId;
        } else {
            user_id = this.currentUserId;
        }
        let author_id;
        let email_from;
        if (user_id) {
            const author = this._getRecords('res.users', [['id', '=', user_id]])[0];
            author_id = author.partner_id;
            email_from = `${author.display_name} <${author.email}>`;
        } else {
            author_id = false;
            // simpler fallback than catchall_formatted
            email_from = mailChannel.anonymous_name || "catchall@example.com";
        }
        // supposedly should convert plain text to html
        const body = message_content;
        // ideally should be posted with mail_create_nosubscribe=True
        return this._mockMailChannelMessagePost(
            mailChannel.id,
            {
                author_id,
                email_from,
                body,
                message_type: 'comment',
                subtype_xmlid: 'mail.mt_comment',
            },
            context
        );
    },
    /**
     * Simulates `/mail/get_suggested_recipients` route.
     *
     * @private
     * @returns {string} model
     * @returns {integer[]} res_ids
     * @returns {Object}
     */
    _mockRouteMailGetSuggestedRecipient(model, res_ids) {
        if (model === 'res.fake') {
            return this._mockResFake_MessageGetSuggestedRecipients(model, res_ids);
        }
        return this._mockMailThread_MessageGetSuggestedRecipients(model, res_ids);
    },
    /**
     * Simulates the `/mail/init_messaging` route.
     *
     * @private
     * @returns {Object}
     */
    _mockRouteMailInitMessaging() {
        return this._mockResUsers_InitMessaging([this.currentUserId]);
    },
    /**
     * Simulates the `/mail/load_message_failures` route.
     *
     * @private
     * @returns {Object[]}
     */
    _mockRouteMailLoadMessageFailures() {
        return this._mockResPartner_MessageFetchFailed(this.currentPartnerId);
    },
    /**
     * Simulates the `/mail/history/messages` route.
     *
     * @private
     * @returns {Object}
     */
    _mockRouteMailMessageHistory(min_id = false, max_id = false, limit = 30) {
        const domain = [['needaction', '=', false]];
        return this._mockMailMessage_MessageFetch(domain, max_id, min_id, limit);
    },
    /**
     * Simulates the `/mail/inbox/messages` route.
     *
     * @private
     * @returns {Object}
     */
    _mockRouteMailMessageInbox(min_id = false, max_id = false, limit = 30) {
        const domain = [['needaction', '=', true]];
        return this._mockMailMessage_MessageFetch(domain, max_id, min_id, limit);
    },
    /**
     * Simulates the `/mail/starred/messages` route.
     *
     * @private
     * @returns {Object}
     */
    _mockRouteMailMessageStarredMessages(min_id = false, max_id = false, limit = 30) {
        const domain = [['starred_partner_ids', 'in', [this.currentPartnerId]]];
        return this._mockMailMessage_MessageFetch(domain, max_id, min_id, limit);
    },
    /**
     * Simulates the `/mail/read_followers` route.
     *
     * @private
     * @param {integer[]} follower_ids
     * @returns {Object} one key for list of followers and one for subtypes
     */
    async _mockRouteMailReadFollowers(args) {
        const res_id = args.res_id; // id of record to read the followers
        const res_model = args.res_model; // model of record to read the followers
        const followers = this._getRecords('mail.followers', [['res_id', '=', res_id], ['res_model', '=', res_model]]);
        const currentPartnerFollower = followers.find(follower => follower.id === this.currentPartnerId);
        const subtypes = currentPartnerFollower
            ? this._mockRouteMailReadSubscriptionData(currentPartnerFollower.id)
            : false;
        return { followers, subtypes };
    },
    /**
     * Simulates the `/mail/read_subscription_data` route.
     *
     * @private
     * @param {integer} follower_id
     * @returns {Object[]} list of followed subtypes
     */
    async _mockRouteMailReadSubscriptionData(follower_id) {
        const follower = this._getRecords('mail.followers', [['id', '=', follower_id]])[0];
        const subtypes = this._getRecords('mail.message.subtype', [
            '&',
            ['hidden', '=', false],
            '|',
            ['res_model', '=', follower.res_model],
            ['res_model', '=', false],
        ]);
        const subtypes_list = subtypes.map(subtype => {
            const parent = this._getRecords('mail.message.subtype', [
                ['id', '=', subtype.parent_id],
            ])[0];
            return {
                'default': subtype.default,
                'followed': follower.subtype_ids.includes(subtype.id),
                'id': subtype.id,
                'internal': subtype.internal,
                'name': subtype.name,
                'parent_model': parent ? parent.res_model : false,
                'res_model': subtype.res_model,
                'sequence': subtype.sequence,
            };
        });
        // NOTE: server is also doing a sort here, not reproduced for simplicity
        return subtypes_list;
    },

    /**
     * Simulates the `/mail/thread/messages` route.
     *
     * @private
     * @param {string} res_model
     * @param {integer} res_id
     * @param {integer} max_id
     * @param {integer} min_id
     * @param {integer} limit
     * @returns {Object[]} list of messages
     */
    async _mockRouteMailThreadFetchMessages(res_model, res_id, max_id = false, min_id = false, limit = 30) {
        const domain = [
            ['res_id', '=', res_id],
            ['model', '=', res_model],
            ['message_type', '!=', 'user_notification'],
        ];
        return this._mockMailMessage_MessageFetch(domain, max_id, min_id, limit);
    },

    //--------------------------------------------------------------------------
    // Private Mocked Methods
    //--------------------------------------------------------------------------

    /**
     * Simulates `get_activity_data` on `mail.activity`.
     *
     * @private
     * @param {string} res_model
     * @param {string} domain
     * @returns {Object}
     */
    _mockMailActivityGetActivityData(res_model, domain) {
        const self = this;
        const records = this._getRecords(res_model, domain);

        const activityTypes = this._getRecords('mail.activity.type', []);
        const activityIds = _.pluck(records, 'activity_ids').flat();

        const groupedActivities = {};
        const resIdToDeadline = {};
        const groups = self._mockReadGroup('mail.activity', {
            domain: [['id', 'in', activityIds]],
            fields: ['res_id', 'activity_type_id', 'ids:array_agg(id)', 'date_deadline:min(date_deadline)'],
            groupby: ['res_id', 'activity_type_id'],
            lazy: false,
        });
        groups.forEach(function (group) {
            // mockReadGroup doesn't correctly return all asked fields
            const activites = self._getRecords('mail.activity', group.__domain);
            group.activity_type_id = group.activity_type_id[0];
            let minDate;
            activites.forEach(function (activity) {
                if (!minDate || moment(activity.date_deadline) < moment(minDate)) {
                    minDate = activity.date_deadline;
                }
            });
            group.date_deadline = minDate;
            resIdToDeadline[group.res_id] = minDate;
            let state;
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
                let mailTemplates = [];
                if (type.mail_template_ids) {
                    mailTemplates = type.mail_template_ids.map(function (id) {
                        const template = _.findWhere(self.data['mail.template'].records, { id: id });
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
     * Simulates `action_unfollow` on `mail.channel`.
     *
     * @private
     * @param {integer[]} ids
     */
    _mockMailChannelActionUnfollow(ids) {
        const channel = this._getRecords('mail.channel', [['id', 'in', ids]])[0];
        if (!channel.members.includes(this.currentPartnerId)) {
            return true;
        }
        this._mockWrite('mail.channel', [
            [channel.id],
            {
                is_pinned: false,
                members: [[3, this.currentPartnerId]],
            },
        ]);
        this._widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.channel/leave',
            payload: {
                id: channel.id,
            },
        }]);
        /**
         * Leave message not posted here because it would send the new message
         * notification on a separate bus notification list from the unsubscribe
         * itself which would lead to the channel being pinned again (handler
         * for unsubscribe is weak and is relying on both of them to be sent
         * together on the bus).
         */
        // this._mockMailChannelMessagePost(channel.id, {
        //     author_id: this.currentPartnerId,
        //     body: '<div class="o_mail_notification">left the channel</div>',
        //     subtype_xmlid: "mail.mt_comment",
        // });
        return true;
    },
    /**
     * Simulates `add_members` on `mail.channel`.
     * For simplicity only handles the current partner joining himself.
     *
     * @private
     * @param {integer[]} ids
     * @param {integer[]} partner_ids
     */
    _mockMailChannelAddMembers(ids, partner_ids) {
        const id = ids[0]; // ensure one
        const channel = this._getRecords('mail.channel', [['id', '=', id]])[0];
        // channel.partner not handled here for simplicity
        if (!channel.is_pinned) {
            this._mockWrite('mail.channel', [
                [channel.id],
                { is_pinned: true },
            ]);
            const body = `<div class="o_mail_notification">joined <a href="#" class="o_channel_redirect" data-oe-id="${channel.id}">#${channel.name}</a></div>`;
            const message_type = "notification";
            const subtype_xmlid = "mail.mt_comment";
            this._mockMailChannelMessagePost(
                [channel.id],
                { body, message_type, subtype_xmlid },
            );
        }
        this._widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.channel/joined',
            payload: {
                'channel': this._mockMailChannelChannelInfo([channel.id])[0],
                'invited_by_user_id': this.currentUserId,
            },
        }]);
    },
    /**
     * Simulates `_broadcast` on `mail.channel`.
     *
     * @private
     * @param {integer} id
     * @param {integer[]} partner_ids
     * @returns {Object}
     */
    _mockMailChannel_broadcast(ids, partner_ids) {
        const notifications = this._mockMailChannel_channelChannelNotifications(ids, partner_ids);
        this._widget.call('bus_service', 'trigger', 'notification', notifications);
    },
    /**
     * Simulates `_channel_channel_notifications` on `mail.channel`.
     *
     * @private
     * @param {integer} id
     * @param {integer[]} partner_ids
     * @returns {Object}
     */
    _mockMailChannel_channelChannelNotifications(ids, partner_ids) {
        const notifications = [];
        for (const partner_id of partner_ids) {
            const user = this._getRecords('res.users', [['partner_id', 'in', partner_id]])[0];
            if (!user) {
                continue;
            }
            // Note: `channel_info` on the server is supposed to be called with
            // the proper user context, but this is not done here for simplicity
            // of not having `channel.partner`.
            const channelInfos = this._mockMailChannelChannelInfo(ids);
            for (const channelInfo of channelInfos) {
                notifications.push({
                    type: 'mail.channel/legacy_insert',
                    payload: {
                        id: channelInfo.id,
                        state: channelInfo.is_minimized ? 'open' : 'closed',
                    },
                });
            }
        }
        return notifications;
    },
    /**
     * Simulates `channel_fetched` on `mail.channel`.
     *
     * @private
     * @param {integer[]} ids
     * @param {string} extra_info
     */
    _mockMailChannelChannelFetched(ids) {
        const channels = this._getRecords('mail.channel', [['id', 'in', ids]]);
        for (const channel of channels) {
            const channelMessages = this._getRecords('mail.message', [
                ['model', '=', 'mail.channel'],
                ['res_id', '=', channel.id],
            ]);
            const lastMessage = channelMessages.reduce((lastMessage, message) => {
                if (message.id > lastMessage.id) {
                    return message;
                }
                return lastMessage;
            }, channelMessages[0]);
            if (!lastMessage) {
                continue;
            }
            this._mockWrite('mail.channel', [
                [channel.id],
                { fetched_message_id: lastMessage.id },
            ]);
            this._widget.call('bus_service', 'trigger', 'notification', [{
                type: 'mail.channel.partner/fetched',
                payload: {
                    channel_id: channel.id,
                    id: `${channel.id}/${this.currentPartnerId}`, // simulate channel.partner id
                    last_message_id: lastMessage.id,
                    partner_id: this.currentPartnerId,
                },
            }]);
        }
    },
    /**
     * Simulates `channel_fetch_preview` on `mail.channel`.
     *
     * @private
     * @param {integer[]} ids
     * @returns {Object[]} list of channels previews
     */
    _mockMailChannelChannelFetchPreview(ids) {
        const channels = this._getRecords('mail.channel', [['id', 'in', ids]]);
        return channels.map(channel => {
            const channelMessages = this._getRecords('mail.message', [
                ['model', '=', 'mail.channel'],
                ['res_id', '=', channel.id],
            ]);
            const lastMessage = channelMessages.reduce((lastMessage, message) => {
                if (message.id > lastMessage.id) {
                    return message;
                }
                return lastMessage;
            }, channelMessages[0]);
            return {
                id: channel.id,
                last_message: lastMessage ? this._mockMailMessageMessageFormat([lastMessage.id])[0] : false,
            };
        });
    },
    /**
     * Simulates the 'channel_fold' route on `mail.channel`.
     * In particular sends a notification on the bus.
     *
     * @private
     * @param {string} uuid
     * @param {state} [state]
     */
    _mockMailChannelChannelFold(uuid, state) {
        const channel = this._getRecords('mail.channel', [['uuid', '=', uuid]])[0];
        this._mockWrite('mail.channel', [
            [channel.id],
            {
                is_minimized: state !== 'closed',
                state,
            }
        ]);
        const channelInfo = this._mockMailChannelChannelInfo([channel.id])[0];
        this._widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.channel/insert',
            payload: {
                id: channelInfo.id,
                serverFoldState: channelInfo.is_minimized ? 'open' : 'closed',
            },
        }]);
    },
    /**
     * Simulates 'channel_get' on 'mail.channel'.
     *
     * @private
     * @param {integer[]} [partners_to=[]]
     * @param {boolean} [pin=true]
     * @returns {Object}
     */
    _mockMailChannelChannelGet(partners_to = [], pin = true) {
        if (partners_to.length === 0) {
            return false;
        }
        if (!partners_to.includes(this.currentPartnerId)) {
            partners_to.push(this.currentPartnerId);
        }
        const partners = this._getRecords('res.partner', [['id', 'in', partners_to]]);

        // NOTE: this mock is not complete, which is done for simplicity.
        // Indeed if a chat already exists for the given partners, the server
        // is supposed to return this existing chat. But the mock is currently
        // always creating a new chat, because no test is relying on receiving
        // an existing chat.
        const id = this._mockCreate('mail.channel', {
            channel_type: 'chat',
            is_minimized: true,
            is_pinned: true,
            last_interest_dt: datetime_to_str(new Date()),
            members: [[6, 0, partners_to]],
            name: partners.map(partner => partner.name).join(", "),
            public: 'private',
            state: 'open',
        });
        return this._mockMailChannelChannelInfo([id])[0];
    },
    /**
     * Simulates `channel_info` on `mail.channel`.
     *
     * @private
     * @param {integer[]} ids
     * @returns {Object[]}
     */
    _mockMailChannelChannelInfo(ids) {
        const channels = this._getRecords('mail.channel', [['id', 'in', ids]]);
        const all_partners = [...new Set(channels.reduce((all_partners, channel) => {
            return [...all_partners, ...channel.members];
        }, []))];
        const direct_partners = [...new Set(channels.reduce((all_partners, channel) => {
            if (channel.channel_type === 'chat') {
                return [...all_partners, ...channel.members];
            }
            return all_partners;
        }, []))];
        const partnerInfos = this._mockMailChannelPartnerInfo(all_partners, direct_partners);
        return channels.map(channel => {
            const members = channel.members.map(partnerId => partnerInfos[partnerId]);
            const messages = this._getRecords('mail.message', [
                ['model', '=', 'mail.channel'],
                ['res_id', '=', channel.id],
            ]);
            const lastMessageId = messages.reduce((lastMessageId, message) => {
                if (!lastMessageId || message.id > lastMessageId) {
                    return message.id;
                }
                return lastMessageId;
            }, undefined);
            const messageNeedactionCounter = this._getRecords('mail.notification', [
                ['res_partner_id', '=', this.currentPartnerId],
                ['is_read', '=', false],
                ['mail_message_id', 'in', messages.map(message => message.id)],
            ]).length;
            const res = Object.assign({}, channel, {
                last_message_id: lastMessageId,
                members,
                message_needaction_counter: messageNeedactionCounter,
            });
            if (channel.channel_type === 'channel') {
                delete res.members;
            } else {
                res['seen_partners_info'] = [{
                    partner_id: this.currentPartnerId,
                    seen_message_id: channel.seen_message_id,
                    fetched_message_id: channel.fetched_message_id,
                }];
            }
            return res;
        });
    },
    /**
     * Simulates the `channel_pin` method of `mail.channel`.
     *
     * @private
     * @param {string} uuid
     * @param {boolean} [pinned=false]
     */
    async _mockMailChannelChannelPin(uuid, pinned = false) {
        const channel = this._getRecords('mail.channel', [['uuid', '=', uuid]])[0];
        this._mockWrite('mail.channel', [
            [channel.id],
            { is_pinned: false },
        ]);
        if (!pinned) {
            this._widget.call('bus_service', 'trigger', 'notification', [{
                type: 'mail.channel/unpin',
                payload: { id: channel.id },
            }]);
        } else {
            this._widget.call('bus_service', 'trigger', 'notification', [{
                type: 'mail.channel/legacy_insert',
                payload: this._mockMailChannelChannelInfo([channel.id])[0],
            }]);
        }
    },
    /**
     * Simulates the `_channel_seen` method of `mail.channel`.
     *
     * @private
     * @param integer[] ids
     * @param {integer} last_message_id
     */
    async _mockMailChannel_ChannelSeen(ids, last_message_id) {
        // Update record
        const channel_id = ids[0];
        if (!channel_id) {
            throw new Error('Should only be one channel in channel_seen mock params');
        }
        const channel = this._getRecords('mail.channel', [['id', '=', channel_id]])[0];
        const messagesBeforeGivenLastMessage = this._getRecords('mail.message', [
            ['id', '<=', last_message_id],
            ['model', '=', 'mail.channel'],
            ['res_id', '=', channel.id],
        ]);
        if (!messagesBeforeGivenLastMessage || messagesBeforeGivenLastMessage.length === 0) {
            return;
        }
        if (!channel) {
            return;
        }
        if (channel.seen_message_id && channel.seen_message_id >= last_message_id) {
            return;
        }
        this._mockMailChannel_SetLastSeenMessage([channel.id], last_message_id);
        this._widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.channel.partner/seen',
            payload: {
                channel_id: channel.id,
                last_message_id,
                partner_id: this.currentPartnerId,
            },
        }]);
    },
    /**
     * Simulates `channel_rename` on `mail.channel`.
     *
     * @private
     * @param {integer[]} ids
     */
    _mockMailChannelChannelRename(ids, name) {
        const channel = this._getRecords('mail.channel', [['id', 'in', ids]])[0];
        this._mockWrite('mail.channel', [
            [channel.id],
            { name },
        ]);
        this._widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.channel/insert',
            payload: {
                id: channel.id,
                name,
            },
        }]);
    },
    /**
     * Simulates `channel_set_custom_name` on `mail.channel`.
     *
     * @private
     * @param {integer[]} ids
     */
    _mockMailChannelChannelSetCustomName(ids, name) {
        const channel = this._getRecords('mail.channel', [['id', 'in', ids]])[0];
        this._mockWrite('mail.channel', [
            [channel.id],
            { custom_channel_name: name },
        ]);
        this._widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.channel/insert',
            payload: {
                id: channel.id,
                custom_channel_name: name,
            },
        }]);
    },
    /**
     * Simulates the `/mail/create_group` route.
     *
     * @private
     * @param {integer[]} partners_to
     * @returns {Object}
     */
    async _mockMailChannelCreateGroup(partners_to) {
        const partners = this._getRecords('res.partner', [['id', 'in', partners_to]]);
        const id = this._mockCreate('mail.channel', {
            channel_type: 'group',
            is_pinned: true,
            members: [[6, 0, partners.map(partner => partner.id)]],
            name: '',
            public: 'private',
            state: 'open',
        });
        this._mockMailChannel_broadcast(id, partners.map(partner => partner.id));
        return this._mockMailChannelChannelInfo([id])[0];
    },
    /**
     * Simulates `execute_command_leave` on `mail.channel`.
     *
     * @private
     */
    _mockMailChannelExecuteCommandLeave(args) {
        const channel = this._getRecords('mail.channel', [['id', 'in', args.args[0]]])[0];
        if (channel.channel_type === 'channel') {
            this._mockMailChannelActionUnfollow([channel.id]);
        } else {
            this._mockMailChannelChannelPin(channel.uuid, false);
        }
    },
    /**
     * Simulates `execute_command_who` on `mail.channel`.
     *
     * @private
     */
    _mockMailChannelExecuteCommandWho(args) {
        const ids = args.args[0];
        const channels = this._getRecords('mail.channel', [['id', 'in', ids]]);
        for (const channel of channels) {
            const members = channel.members.map(memberId => this._getRecords('res.partner', [['id', '=', memberId]])[0].name);
            let message = "You are alone in this channel.";
            if (members.length > 0) {
                message = `Users in this channel: ${members.join(', ')} and you`;
            }
            this._widget.call('bus_service', 'trigger', 'notification', [{
                type: 'mail.channel/transient_message',
                payload: {
                    'body': `<span class="o_mail_notification">${message}</span>`,
                    'model': 'mail.channel',
                    'res_id': channel.id,
                }
            }]);
        }
    },
    /**
     * Simulates `get_mention_suggestions` on `mail.channel`.
     *
     * @private
     * @returns {Array[]}
     */
    _mockMailChannelGetMentionSuggestions(args) {
        const search = args.kwargs.search || '';
        const limit = args.kwargs.limit || 8;

        /**
         * Returns the given list of channels after filtering it according to
         * the logic of the Python method `get_mention_suggestions` for the
         * given search term. The result is truncated to the given limit and
         * formatted as expected by the original method.
         *
         * @param {Object[]} channels
         * @param {string} search
         * @param {integer} limit
         * @returns {Object[]}
         */
        const mentionSuggestionsFilter = function (channels, search, limit) {
            const matchingChannels = channels
                .filter(channel => {
                    // no search term is considered as return all
                    if (!search) {
                        return true;
                    }
                    // otherwise name or email must match search term
                    if (channel.name && channel.name.includes(search)) {
                        return true;
                    }
                    return false;
                }).map(channel => {
                    // expected format
                    return {
                        id: channel.id,
                        name: channel.name,
                        public: channel.public,
                    };
                });
            // reduce results to max limit
            matchingChannels.length = Math.min(matchingChannels.length, limit);
            return matchingChannels;
        };

        const mentionSuggestions = mentionSuggestionsFilter(this.data['mail.channel'].records, search, limit);

        return mentionSuggestions;
    },
    /**
     * Simulates `write` on `mail.channel` when `image_128` changes.
     *
     * @param {integer} id
     */
    _mockMailChannelWriteImage128(id) {
        this._mockWrite('mail.channel', [
            [id],
            {
                avatarCacheKey: moment.utc().format("YYYYMMDDHHmmss"),
            },
        ]);
        const avatarCacheKey = this._getRecords('mail.channel', [['id', '=', id]])[0].avatarCacheKey;
        this._widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.channel/insert',
            payload: {
                id: 20,
                avatarCacheKey: avatarCacheKey,
            },
        }]);
    },
    /**
     * Simulates `message_post` on `mail.channel`.
     *
     * @private
     * @param {integer} id
     * @param {Object} kwargs
     * @param {Object} [context]
     * @returns {integer|false}
     */
    _mockMailChannelMessagePost(id, kwargs, context) {
        const message_type = kwargs.message_type || 'notification';
        const channel = this._getRecords('mail.channel', [['id', '=', id]])[0];
        if (channel.channel_type !== 'channel') {
            // channel.partner not handled here for simplicity
            this._mockWrite('mail.channel', [
                [channel.id],
                {
                    last_interest_dt: datetime_to_str(new Date()),
                    is_pinned: true,
                },
            ]);
        }
        const messageData = this._mockMailThreadMessagePost(
            'mail.channel',
            [id],
            Object.assign(kwargs, {
                message_type,
            }),
            context,
        );
        if (kwargs.author_id === this.currentPartnerId) {
            this._mockMailChannel_SetLastSeenMessage([channel.id], messageData.id);
        } else {
            this._mockWrite('mail.channel', [
                [channel.id],
                { message_unread_counter: (channel.message_unread_counter || 0) + 1 },
            ]);
        }
        return messageData;
    },
    /**
     * Simulates `notify_typing` on `mail.channel`.
     *
     * @private
     * @param {integer[]} ids
     * @param {boolean} is_typing
     * @param {Object} [context={}]
     */
    _mockMailChannelNotifyTyping(ids, is_typing, context = {}) {
        const channels = this._getRecords('mail.channel', [['id', 'in', ids]]);
        let partner_id;
        if ('mockedPartnerId' in context) {
            partner_id = context.mockedPartnerId;
        } else {
            partner_id = this.currentPartnerId;
        }
        const partner = this._getRecords('res.partner', [['id', '=', partner_id]]);
        const notifications = [];
        for (const channel of channels) {
            const data = {
                type: 'mail.channel.partner/typing_status',
                payload: {
                    channel_id: channel.id,
                    is_typing: is_typing,
                    partner_id: partner_id,
                    partner_name: partner.name,
                },
            };
            notifications.push([data]);
        }
        this._widget.call('bus_service', 'trigger', 'notification', notifications);
    },
    /**
     * Simulates `_get_channel_partner_info` on `mail.channel`.
     *
     * @private
     * @param {integer[]} all_partners
     * @param {integer[]} direct_partners
     * @returns {Object[]}
     */
    _mockMailChannelPartnerInfo(all_partners, direct_partners) {
        const partners = this._getRecords(
            'res.partner',
            [['id', 'in', all_partners]],
            { active_test: false },
        );
        const partnerInfos = {};
        for (const partner of partners) {
            const partnerInfo = {
                email: partner.email,
                id: partner.id,
                name: partner.name,
            };
            if (direct_partners.includes(partner.id)) {
                partnerInfo.im_status = partner.im_status;
            }
            partnerInfos[partner.id] = partnerInfo;
        }
        return partnerInfos;
    },
    /**
     * Simulates the `_set_last_seen_message` method of `mail.channel`.
     *
     * @private
     * @param {integer[]} ids
     * @param {integer} message_id
     */
    _mockMailChannel_SetLastSeenMessage(ids, message_id) {
        this._mockWrite('mail.channel', [ids, {
            fetched_message_id: message_id,
            seen_message_id: message_id,
        }]);
    },
    /**
     * Simulates `mark_all_as_read` on `mail.message`.
     *
     * @private
     * @param {Array[]} [domain]
     * @returns {integer[]}
     */
    _mockMailMessageMarkAllAsRead(domain) {
        const notifDomain = [
            ['res_partner_id', '=', this.currentPartnerId],
            ['is_read', '=', false],
        ];
        if (domain) {
            const messages = this._getRecords('mail.message', domain);
            const ids = messages.map(messages => messages.id);
            this._mockMailMessageSetMessageDone(ids);
            return ids;
        }
        const notifications = this._getRecords('mail.notification', notifDomain);
        this._mockWrite('mail.notification', [
            notifications.map(notification => notification.id),
            { is_read: true },
        ]);
        const messageIds = [];
        for (const notification of notifications) {
            if (!messageIds.includes(notification.mail_message_id)) {
                messageIds.push(notification.mail_message_id);
            }
        }
        const messages = this._getRecords('mail.message', [['id', 'in', messageIds]]);
        // simulate compute that should be done based on notifications
        for (const message of messages) {
            this._mockWrite('mail.message', [
                [message.id],
                {
                    needaction: false,
                    needaction_partner_ids: message.needaction_partner_ids.filter(
                        partnerId => partnerId !== this.currentPartnerId
                    ),
                },
            ]);
        }
        this._widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.message/mark_as_read',
            payload: {
                message_ids: messageIds,
                needaction_inbox_counter: this._mockResPartner_GetNeedactionCount(this.currentPartnerId),
            },
        }]);
        return messageIds;
    },
    /**
     * Simulates `_message_fetch` on `mail.message`.
     *
     * @private
     * @param {Array[]} domain
     * @param {string} [limit=20]
     * @returns {Object[]}
     */
    async _mockMailMessage_MessageFetch(domain, max_id, min_id, limit = 30) {
        // TODO FIXME delay RPC until next potential render as a workaround
        // to OWL issue (possibly https://github.com/odoo/owl/issues/904)
        await nextAnimationFrame();
        if (max_id) {
            domain.push(['id', '<', max_id]);
        }
        if (min_id) {
            domain.push(['id', '>', min_id]);
        }
        let messages = this._getRecords('mail.message', domain);
        // sorted from highest ID to lowest ID (i.e. from youngest to oldest)
        messages.sort(function (m1, m2) {
            return m1.id < m2.id ? 1 : -1;
        });
        // pick at most 'limit' messages
        messages.length = Math.min(messages.length, limit);
        return this._mockMailMessageMessageFormat(messages.map(message => message.id));
    },
    /**
     * Simulates `message_format` on `mail.message`.
     *
     * @private
     * @returns {integer[]} ids
     * @returns {Object[]}
     */
    _mockMailMessageMessageFormat(ids) {
        const messages = this._getRecords('mail.message', [['id', 'in', ids]]);
        // sorted from highest ID to lowest ID (i.e. from most to least recent)
        messages.sort(function (m1, m2) {
            return m1.id < m2.id ? 1 : -1;
        });
        return messages.map(message => {
            const thread = message.model && this._getRecords(message.model, [
                ['id', '=', message.res_id],
            ])[0];
            let formattedAuthor;
            if (message.author_id) {
                const author = this._getRecords(
                    'res.partner',
                    [['id', '=', message.author_id]],
                    { active_test: false }
                )[0];
                formattedAuthor = [author.id, author.display_name];
            } else {
                formattedAuthor = [0, message.email_from];
            }
            const attachments = this._getRecords('ir.attachment', [
                ['id', 'in', message.attachment_ids],
            ]);
            const formattedAttachments = attachments.map(attachment => {
                return Object.assign({
                    'checksum': attachment.checksum,
                    'id': attachment.id,
                    'filename': attachment.name,
                    'name': attachment.name,
                    'mimetype': attachment.mimetype,
                    'is_main': thread && thread.message_main_attachment_id === attachment.id,
                    'res_id': attachment.res_id || messages.res_id,
                    'res_model': attachment.res_model || message.model,
                });
            });
            const allNotifications = this._getRecords('mail.notification', [
                ['mail_message_id', '=', message.id],
            ]);
            const historyPartnerIds = allNotifications
                .filter(notification => notification.is_read)
                .map(notification => notification.res_partner_id);
            const needactionPartnerIds = allNotifications
                .filter(notification => !notification.is_read)
                .map(notification => notification.res_partner_id);
            let notifications = this._mockMailNotification_FilteredForWebClient(
                allNotifications.map(notification => notification.id)
            );
            notifications = this._mockMailNotification_NotificationFormat(
                notifications.map(notification => notification.id)
            );
            const trackingValueIds = this._getRecords('mail.tracking.value', [
                ['id', 'in', message.tracking_value_ids],
            ]);
            const partners = this._getRecords(
                'res.partner',
                [['id', 'in', message.partner_ids]],
            );
            const response = Object.assign({}, message, {
                attachment_ids: formattedAttachments,
                author_id: formattedAuthor,
                history_partner_ids: historyPartnerIds,
                needaction_partner_ids: needactionPartnerIds,
                notifications,
                recipients: partners.map(p => ({ id: p.id, name: p.name })),
                tracking_value_ids: trackingValueIds,
            });
            if (message.subtype_id) {
                const subtype = this._getRecords('mail.message.subtype', [
                    ['id', '=', message.subtype_id],
                ])[0];
                response.subtype_description = subtype.description;
            }
            return response;
        });
    },
    /**
     * Simulates `_message_notification_format` on `mail.message`.
     *
     * @private
     * @returns {integer[]} ids
     * @returns {Object[]}
     */
    _mockMailMessage_MessageNotificationFormat(ids) {
        const messages = this._getRecords('mail.message', [['id', 'in', ids]]);
        return messages.map(message => {
            let notifications = this._getRecords('mail.notification', [
                ['mail_message_id', '=', message.id],
            ]);
            notifications = this._mockMailNotification_FilteredForWebClient(
                notifications.map(notification => notification.id)
            );
            notifications = this._mockMailNotification_NotificationFormat(
                notifications.map(notification => notification.id)
            );
            return {
                'date': message.date,
                'id': message.id,
                'message_type': message.message_type,
                'model': message.model,
                'notifications': notifications,
                'res_id': message.res_id,
                'res_model_name': message.res_model_name,
            };
        });
    },
    /**
     * Simulates `set_message_done` on `mail.message`, which turns provided
     * needaction message to non-needaction (i.e. they are marked as read from
     * from the Inbox mailbox). Also notify on the longpoll bus that the
     * messages have been marked as read, so that UI is updated.
     *
     * @private
     * @param {integer[]} ids
     */
    _mockMailMessageSetMessageDone(ids) {
        const messages = this._getRecords('mail.message', [['id', 'in', ids]]);

        const notifications = this._getRecords('mail.notification', [
            ['res_partner_id', '=', this.currentPartnerId],
            ['is_read', '=', false],
            ['mail_message_id', 'in', messages.map(messages => messages.id)]
        ]);
        this._mockWrite('mail.notification', [
            notifications.map(notification => notification.id),
            { is_read: true },
        ]);
        // simulate compute that should be done based on notifications
        for (const message of messages) {
            this._mockWrite('mail.message', [
                [message.id],
                {
                    needaction: false,
                    needaction_partner_ids: message.needaction_partner_ids.filter(
                        partnerId => partnerId !== this.currentPartnerId
                    ),
                },
            ]);
            this._widget.call('bus_service', 'trigger', 'notification', [{
                type: 'mail.message/mark_as_read',
                payload: {
                    message_ids: [message.id],
                    needaction_inbox_counter: this._mockResPartner_GetNeedactionCount(this.currentPartnerId),
                },
            }]);
        }
    },
    /**
     * Simulates `toggle_message_starred` on `mail.message`.
     *
     * @private
     * @returns {integer[]} ids
     */
    _mockMailMessageToggleMessageStarred(ids) {
        const messages = this._getRecords('mail.message', [['id', 'in', ids]]);
        for (const message of messages) {
            const wasStared = message.starred_partner_ids.includes(this.currentPartnerId);
            this._mockWrite('mail.message', [
                [message.id],
                { starred_partner_ids: [[wasStared ? 3 : 4, this.currentPartnerId]] }
            ]);
            this._widget.call('bus_service', 'trigger', 'notification', [{
                type: 'mail.message/toggle_star',
                payload: {
                    message_ids: [message.id],
                    starred: !wasStared,
                },
            }]);
        }
    },
    /**
     * Simulates `unstar_all` on `mail.message`.
     *
     * @private
     */
    _mockMailMessageUnstarAll() {
        const messages = this._getRecords('mail.message', [
            ['starred_partner_ids', 'in', this.currentPartnerId],
        ]);
        this._mockWrite('mail.message', [
            messages.map(message => message.id),
            { starred_partner_ids: [[3, this.currentPartnerId]] }
        ]);
        this._widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.message/toggle_star',
            payload: {
                message_ids: messages.map(message => message.id),
                starred: false,
            },
        }]);
    },
    /**
     * Simulates `_filtered_for_web_client` on `mail.notification`.
     *
     * @private
     * @returns {integer[]} ids
     * @returns {Object[]}
     */
    _mockMailNotification_FilteredForWebClient(ids) {
        const notifications = this._getRecords('mail.notification', [
            ['id', 'in', ids],
            ['notification_type', '!=', 'inbox'],
        ]);
        return notifications.filter(notification => {
            const partner = this._getRecords('res.partner', [['id', '=', notification.res_partner_id]])[0];
            return Boolean(
                ['bounce', 'exception', 'canceled'].includes(notification.notification_status) ||
                (partner && partner.partner_share)
            );
        });
    },
    /**
     * Simulates `_notification_format` on `mail.notification`.
     *
     * @private
     * @returns {integer[]} ids
     * @returns {Object[]}
     */
    _mockMailNotification_NotificationFormat(ids) {
        const notifications = this._getRecords('mail.notification', [['id', 'in', ids]]);
        return notifications.map(notification => {
            const partner = this._getRecords('res.partner', [['id', '=', notification.res_partner_id]])[0];
            return {
                'id': notification.id,
                'notification_type': notification.notification_type,
                'notification_status': notification.notification_status,
                'failure_type': notification.failure_type,
                'res_partner_id': partner ? [partner && partner.id, partner && partner.display_name] : undefined,
            };
        });
    },
    /**
     * Simulates `_message_compute_author` on `mail.thread`.
     *
     * @private
     * @param {string} model
     * @param {integer[]} ids
     * @param {Object} [context={}]
     * @returns {Array}
     */
    _MockMailThread_MessageComputeAuthor(model, ids, author_id, email_from, context = {}) {
        if (author_id === undefined) {
            // For simplicity partner is not guessed from email_from here, but
            // that would be the first step on the server.
            let user_id;
            if ('mockedUserId' in context) {
                // can be falsy to simulate not being logged in
                user_id = context.mockedUserId
                    ? context.mockedUserId
                    : this.publicUserId;
            } else {
                user_id = this.currentUserId;
            }
            const user = this._getRecords(
                'res.users',
                [['id', '=', user_id]],
                { active_test: false },
            )[0];
            const author = this._getRecords(
                'res.partner',
                [['id', '=', user.partner_id]],
                { active_test: false },
            )[0];
            author_id = author.id;
            email_from = `${author.display_name} <${author.email}>`;
        }

        if (email_from === undefined) {
            if (author_id) {
                const author = this._getRecords(
                    'res.partner',
                    [['id', '=', author_id]],
                    { active_test: false },
                )[0];
                email_from = `${author.display_name} <${author.email}>`;
            }
        }

        if (!email_from) {
            throw Error("Unable to log message due to missing author email.");
        }

        return [author_id, email_from];
    },
    /**
     * Simulates `_message_add_suggested_recipient` on `mail.thread`.
     *
     * @private
     * @param {string} model
     * @param {integer[]} ids
     * @param {Object} result
     * @param {Object} [param3={}]
     * @param {string} [param3.email]
     * @param {integer} [param3.partner]
     * @param {string} [param3.reason]
     * @returns {Object}
     */
    _mockMailThread_MessageAddSuggestedRecipient(model, ids, result, { email, partner, reason = '' } = {}) {
        const record = this._getRecords(model, [['id', 'in', 'ids']])[0];
        // for simplicity
        result[record.id].push([partner, email, reason]);
        return result;
    },
    /**
     * Simulates `_message_get_suggested_recipients` on `mail.thread`.
     *
     * @private
     * @param {string} model
     * @param {integer[]} ids
     * @returns {Object}
     */
    _mockMailThread_MessageGetSuggestedRecipients(model, ids) {
        const result = ids.reduce((result, id) => result[id] = [], {});
        const records = this._getRecords(model, [['id', 'in', ids]]);
        for (const record in records) {
            if (record.user_id) {
                const user = this._getRecords('res.users', [['id', '=', record.user_id]]);
                if (user.partner_id) {
                    const reason = this.data[model].fields['user_id'].string;
                    this._mockMailThread_MessageAddSuggestedRecipient(result, user.partner_id, reason);
                }
            }
        }
        return result;
    },
    /**
     * Simulates `_message_get_suggested_recipients` on `res.fake`.
     *
     * @private
     * @param {string} model
     * @param {integer[]} ids
     * @returns {Object}
     */
    _mockResFake_MessageGetSuggestedRecipients(model, ids) {
        const result = {};
        const records = this._getRecords(model, [['id', 'in', ids]]);

        for (const record of records) {
            result[record.id] = [];
            if (record.email_cc) {
                result[record.id].push([
                    false,
                    record.email_cc,
                    'CC email',
                ]);
            }
            const partners = this._getRecords(
                'res.partner',
                [['id', 'in', record.partner_ids]],
            );
            if (partners.length) {
                for (const partner of partners) {
                    result[record.id].push([
                        partner.id,
                        partner.display_name,
                        'Email partner',
                    ]);
                }
            }
        }

        return result;
    },
    /**
     * Simulates `message_post` on `mail.thread`.
     *
     * @private
     * @param {string} model
     * @param {integer[]} ids
     * @param {Object} kwargs
     * @param {Object} [context]
     * @returns {Object}
     */
    _mockMailThreadMessagePost(model, ids, kwargs, context) {
        const id = ids[0]; // ensure_one
        if (kwargs.attachment_ids) {
            const attachments = this._getRecords('ir.attachment', [
                ['id', 'in', kwargs.attachment_ids],
                ['res_model', '=', 'mail.compose.message'],
                ['res_id', '=', 0],
            ]);
            const attachmentIds = attachments.map(attachment => attachment.id);
            this._mockWrite('ir.attachment', [
                attachmentIds,
                {
                    res_id: id,
                    res_model: model,
                },
            ]);
            kwargs.attachment_ids = attachmentIds.map(attachmentId => [4, attachmentId]);
        }
        const subtype_xmlid = kwargs.subtype_xmlid || 'mail.mt_note';
        const [author_id, email_from] = this._MockMailThread_MessageComputeAuthor(
            model,
            ids,
            kwargs.author_id,
            kwargs.email_from, context,
        );
        const values = Object.assign({}, kwargs, {
            author_id,
            email_from,
            is_discussion: subtype_xmlid === 'mail.mt_comment',
            is_note: subtype_xmlid === 'mail.mt_note',
            model,
            res_id: id,
        });
        delete values.subtype_xmlid;
        const messageId = this._mockCreate('mail.message', values);
        this._mockMailThread_NotifyThread(model, ids, messageId);
        return this._mockMailMessageMessageFormat([messageId])[0];
    },
    /**
     * Simulates `message_subscribe` on `mail.thread`.
     *
     * @private
     * @param {string} model not in server method but necessary for thread mock
     * @param {integer[]} ids
     * @param {integer[]} partner_ids
     * @param {integer[]} subtype_ids
     * @returns {boolean}
     */
    _mockMailThreadMessageSubscribe(model, ids, partner_ids, subtype_ids) {
        // message_subscribe is too complex for a generic mock.
        // mockRPC should be considered for a specific result.
    },
    /**
     * Simulates `_notify_thread` on `mail.thread`.
     * Simplified version that sends notification to author and channel.
     *
     * @private
     * @param {string} model not in server method but necessary for thread mock
     * @param {integer[]} ids
     * @param {integer} messageId
     * @returns {boolean}
     */
    _mockMailThread_NotifyThread(model, ids, messageId) {
        const message = this._getRecords('mail.message', [['id', '=', messageId]])[0];
        const messageFormat = this._mockMailMessageMessageFormat([messageId])[0];
        const notifications = [];
        // author
        const notificationData = {
            type: 'author',
            payload: {
                message: messageFormat,
            },
        };
        if (message.author_id) {
            notifications.push([notificationData]);
        }
        // members
        const channels = this._getRecords('mail.channel', [['id', '=', message.res_id]]);
        for (const channel of channels) {
            notifications.push({
                type: 'mail.channel/new_message',
                payload: {
                    id: channel.id,
                    message: messageFormat,
                }
            });

            // notify update of last_interest_dt
            const now = datetime_to_str(new Date());
            this._mockWrite('mail.channel',
                [channel.id],
                { last_interest_dt: now },
            );
            notifications.push({
                type: 'mail.channel/last_interest_dt_changed',
                payload: {
                    id: channel.id,
                    last_interest_dt: now, // channel.partner not used for simplicity
                },
            });
        }
        this._widget.call('bus_service', 'trigger', 'notification', notifications);
    },
    /**
     * Simulates `message_unsubscribe` on `mail.thread`.
     *
     * @private
     * @param {string} model not in server method but necessary for thread mock
     * @param {integer[]} ids
     * @param {integer[]} partner_ids
     * @returns {boolean|undefined}
     */
    _mockMailThreadMessageUnsubscribe(model, ids, partner_ids) {
        if (!partner_ids) {
            return true;
        }
        const followers = this._getRecords('mail.followers', [
            ['res_model', '=', model],
            ['res_id', 'in', ids],
            ['partner_id', 'in', partner_ids || []],
        ]);
        this._mockUnlink(model, [followers.map(follower => follower.id)]);
    },
    /**
     * Simulates `_get_channels_as_member` on `res.partner`.
     *
     * @private
     * @param {integer[]} ids
     * @returns {Object}
     */
    _mockResPartner_GetChannelsAsMember(ids) {
        const partner = this._getRecords('res.partner', [['id', 'in', ids]])[0];
        const channels = this._getRecords('mail.channel', [
            ['channel_type', 'in', ['channel', 'group']],
            ['members', 'in', partner.id],
        ]);
        const directMessages = this._getRecords('mail.channel', [
            ['channel_type', '=', 'chat'],
            ['is_pinned', '=', true],
            ['members', 'in', partner.id],
        ]);
        return [
            ...channels,
            ...directMessages,
        ];
    },

    /**
     * Simulates `_find_or_create_for_user` on `res.users.settings`.
     *
     * @param {Object} user
     * @returns {Object}
     */
    _mockResUsersSettings_FindOrCreateForUser(user_id) {
        let settings = this._getRecords('res.users.settings', [['user_id', '=', user_id]])[0];
        if (!settings) {
            const settingsId = this._mockCreate('res.users.settings', { user_id: user_id });
            settings = this._getRecords('res.users.settings', [['id', '=', settingsId]])[0];
        }
        return settings;
    },

    /**
     * Simulates `set_res_users_settings` on `res.users.settings`.
     *
     * @param {integer} id
     * @param {Object} newSettings
     */
    _mockResUsersSettingsSetResUsersSettings(id, newSettings) {
        const oldSettings = this._getRecords('res.users.settings', [['id', '=', id]])[0];
        const changedSettings = {};
        for (const setting in newSettings) {
            if (setting in oldSettings && newSettings[setting] !== oldSettings[setting]) {
                changedSettings[setting] = newSettings[setting];
            }
        }
        this._mockWrite('res.users.settings', [
            [id],
            changedSettings,
        ]);
        this._widget.call('bus_service', 'trigger', 'notification', [{
            type: 'res.users.settings/changed',
            payload: changedSettings,
        }]);
    },

    /**
     * Simulates `get_mention_suggestions` on `res.partner`.
     *
     * @private
     * @returns {Array[]}
     */
    _mockResPartnerGetMentionSuggestions(args) {
        const search = (args.args[0] || args.kwargs.search || '').toLowerCase();
        const limit = args.args[1] || args.kwargs.limit || 8;

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
        const mentionSuggestionsFilter = (partners, search, limit) => {
            const matchingPartners = [...this._mockResPartnerMailPartnerFormat(
                partners
                    .filter(partner => {
                        // no search term is considered as return all
                        if (!search) {
                            return true;
                        }
                        // otherwise name or email must match search term
                        if (partner.name && partner.name.toLowerCase().includes(search)) {
                            return true;
                        }
                        if (partner.email && partner.email.toLowerCase().includes(search)) {
                            return true;
                        }
                        return false;
                    })
                    .map(partner => partner.id)
            ).values()];
            // reduce results to max limit
            matchingPartners.length = Math.min(matchingPartners.length, limit);
            return matchingPartners;
        };

        // add main suggestions based on users
        const partnersFromUsers = this._getRecords('res.users', [])
            .map(user => this._getRecords('res.partner', [['id', '=', user.partner_id]])[0])
            .filter(partner => partner);
        const mainMatchingPartners = mentionSuggestionsFilter(partnersFromUsers, search, limit);

        let extraMatchingPartners = [];
        // if not enough results add extra suggestions based on partners
        const remainingLimit = limit - mainMatchingPartners.length;
        if (mainMatchingPartners.length < limit) {
            const partners = this._getRecords('res.partner', [['id', 'not in', mainMatchingPartners.map(partner => partner.id)]]);
            extraMatchingPartners = mentionSuggestionsFilter(partners, search, remainingLimit);
        }
        return mainMatchingPartners.concat(extraMatchingPartners);
    },
    /**
     * Simulates `_get_needaction_count` on `res.partner`.
     *
     * @private
     * @param {integer} id
     * @returns {integer}
     */
    _mockResPartner_GetNeedactionCount(id) {
        const partner = this._getRecords('res.partner', [['id', '=', id]])[0];
        return this._getRecords('mail.notification', [
            ['res_partner_id', '=', partner.id],
            ['is_read', '=', false],
        ]).length;
    },
    /**
     * Simulates `im_search` on `res.partner`.
     *
     * @private
     * @param {string} [name='']
     * @param {integer} [limit=20]
     * @returns {Object[]}
     */
    _mockResPartnerImSearch(name = '', limit = 20) {
        name = name.toLowerCase(); // simulates ILIKE
        // simulates domain with relational parts (not supported by mock server)
        const matchingPartners = this._getRecords('res.users', [])
            .filter(user => {
                const partner = this._getRecords('res.partner', [['id', '=', user.partner_id]])[0];
                // user must have a partner
                if (!partner) {
                    return false;
                }
                // not current partner
                if (partner.id === this.currentPartnerId) {
                    return false;
                }
                // no name is considered as return all
                if (!name) {
                    return true;
                }
                if (partner.name && partner.name.toLowerCase().includes(name)) {
                    return true;
                }
                return false;
            }).map(user => {
                const partner = this._getRecords('res.partner', [['id', '=', user.partner_id]])[0];
                return {
                    id: partner.id,
                    im_status: user.im_status || 'offline',
                    email: partner.email,
                    name: partner.name,
                    user_id: user.id,
                };
            }).sort((a, b) => (a.name === b.name) ? (a.id - b.id) : (a.name > b.name) ? 1 : -1);
        matchingPartners.length = Math.min(matchingPartners.length, limit);
        return matchingPartners;
    },
    /**
     * Simulates `mail_partner_format` on `res.partner`.
     *
     * @private
     * @returns {integer[]} ids
     * @returns {Map}
     */
    _mockResPartnerMailPartnerFormat(ids) {
        const partners = this._getRecords(
            'res.partner',
            [['id', 'in', ids]],
            { active_test: false }
        );
        // Servers is also returning `user_id` and `is_internal_user` but not
        // done here for simplification.
        return new Map(partners.map(partner => [
            partner.id,
            {
                "active": partner.active,
                "display_name": partner.display_name,
                "email": partner.email,
                "id": partner.id,
                "im_status": partner.im_status,
                "name": partner.name,
            }
        ]));
    },
    /**
     * Simulates `search_for_channel_invite` on `res.partner`.
     *
     * @private
     * @param {string} [search_term='']
     * @param {integer} [channel_id]
     * @param {integer} [limit=30]
     * @returns {Object[]}
     */
    _mockResPartnerSearchForChannelInvite(search_term, channel_id, limit = 30) {
        search_term = search_term.toLowerCase(); // simulates ILIKE
        // simulates domain with relational parts (not supported by mock server)
        const matchingPartners = [...this._mockResPartnerMailPartnerFormat(
            this._getRecords('res.users', [])
            .filter(user => {
                const partner = this._getRecords('res.partner', [['id', '=', user.partner_id]])[0];
                // user must have a partner
                if (!partner) {
                    return false;
                }
                // not current partner
                if (partner.id === this.currentPartnerId) {
                    return false;
                }
                // no name is considered as return all
                if (!search_term) {
                    return true;
                }
                if (partner.name && partner.name.toLowerCase().includes(search_term)) {
                    return true;
                }
                return false;
            })
            .map(user => user.partner_id)
        ).values()];
        const count = matchingPartners.length;
        matchingPartners.length = Math.min(count, limit);
        return {
            count,
            partners: matchingPartners
        };
    },
    /**
     * Simulates `_message_fetch_failed` on `res.partner`.
     *
     * @private
     * @param {integer} id
     * @returns {Object[]}
     */
    _mockResPartner_MessageFetchFailed(id) {
        const partner = this._getRecords('res.partner', [['id', '=', id]])[0];
        const messages = this._getRecords('mail.message', [
            ['author_id', '=', partner.id],
            ['res_id', '!=', 0],
            ['model', '!=', false],
            ['message_type', '!=', 'user_notification'],
        ]).filter(message => {
            // Purpose is to simulate the following domain on mail.message:
            // ['notification_ids.notification_status', 'in', ['bounce', 'exception']],
            // But it's not supported by _getRecords domain to follow a relation.
            const notifications = this._getRecords('mail.notification', [
                ['mail_message_id', '=', message.id],
                ['notification_status', 'in', ['bounce', 'exception']],
            ]);
            return notifications.length > 0;
        });
        return this._mockMailMessage_MessageNotificationFormat(messages.map(message => message.id));
    },
    /**
     * Simulates `_init_messaging` on `res.users`.
     *
     * @private
     * @param {integer[]} ids
     * @returns {Object}
     */
    _mockResUsers_InitMessaging(ids) {
        const user = this._getRecords('res.users', [['id', 'in', ids]])[0];
        return {
            channels: this._mockMailChannelChannelInfo(this._mockResPartner_GetChannelsAsMember(user.partner_id).map(channel => channel.id)),
            current_partner: this._mockResPartnerMailPartnerFormat(user.partner_id).get(user.partner_id),
            current_user_id: this.currentUserId,
            current_user_settings: this._mockResUsersSettings_FindOrCreateForUser(user.id),
            mail_failures: [],
            menu_id: false, // not useful in QUnit tests
            needaction_inbox_counter: this._mockResPartner_GetNeedactionCount(user.partner_id),
            partner_root: this._mockResPartnerMailPartnerFormat(this.partnerRootId).get(this.partnerRootId),
            public_partners: [...this._mockResPartnerMailPartnerFormat(this.publicPartnerId).values()],
            shortcodes: this._getRecords('mail.shortcode', []),
            starred_counter: this._getRecords('mail.message', [['starred_partner_ids', 'in', user.partner_id]]).length,
        };
    },
});
