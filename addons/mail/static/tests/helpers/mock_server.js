/** @odoo-module **/

// ensure bus mock server is loaded first.
import '@bus/../tests/helpers/mock_server';

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

import { date_to_str, datetime_to_str } from 'web.time';


patch(MockServer.prototype, 'mail', {
    init({ models }) {
        this._super(...arguments);

        if (this.currentPartnerId && models && 'res.partner' in models) {
            this.currentPartner = this.getRecords('res.partner', [['id', '=', this.currentPartnerId]])[0];
        }
        // creation of the ir.model.fields records, required for tracked fields
        for (const modelName in models) {
            const fieldNamesToFields = models[modelName].fields;
            for (const fname in fieldNamesToFields) {
                if (fieldNamesToFields[fname].tracking) {
                    this.mockCreate('ir.model.fields', { model: modelName, name: fname });
                }
            }
        }
    },
    /**
     * @override
     */
    async performRPC(route, args) {
        if (route === '/mail/attachment/upload') {
            const ufile = args.body.get('ufile');
            const is_pending = args.body.get('is_pending') === 'true';
            const model = is_pending ? 'mail.compose.message' : args.body.get('thread_model');
            const id = is_pending ? 0 : parseInt(args.body.get('thread_id'));
            const attachmentId = this.mockCreate('ir.attachment', {
                // datas,
                mimetype: ufile.type,
                name: ufile.name,
                res_id: id,
                res_model: model,
            });
            const attachment = this.getRecords('ir.attachment', [['id', '=', attachmentId]])[0];
            return {
                'filename': attachment.name,
                'id': attachment.id,
                'mimetype': attachment.mimetype,
                'size': attachment.file_size
            };
        }
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _performRPC(route, args) {
        // routes
        if (route === '/longpolling/im_status') {
            const { partner_ids } = args;
            return {
                'partners': this.pyEnv['res.partner'].searchRead([['id', 'in', partner_ids]], { context: { 'active_test': false }, fields: ['im_status'] })
            };
        }
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
        if (route === '/mail/read_subscription_data') {
            const follower_id = args.follower_id;
            return this._mockRouteMailReadSubscriptionData(follower_id);
        }
        if (route === '/mail/thread/data') {
            return this._mockRouteMailThreadData(args.thread_model, args.thread_id, args.request_list);
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
        if (args.model === 'ir.attachment' && args.method === 'register_as_main_attachment') {
            const ids = args.args[0];
            return this._mockIrAttachmentRegisterAsMainAttachment(ids);
        }
        // mail.activity methods
        if (args.model === 'mail.activity' && args.method === 'action_feedback') {
            const ids = args.args[0];
            return this._mockMailActivityActionFeedback(ids);
        }
        if (args.model === 'mail.activity' && args.method === 'action_feedback_schedule_next') {
            const ids = args.args[0];
            return this._mockMailActivityActionFeedbackScheduleNext(ids);
        }
        if (args.model === 'mail.activity' && args.method === 'activity_format') {
            const ids = args.args[0];
            return this._mockMailActivityActivityFormat(ids);
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
        if (args.model === 'mail.channel' && args.method === 'channel_fetch_preview') {
            const ids = args.args[0];
            return this._mockMailChannelChannelFetchPreview(ids);
        }
        if (args.model === 'mail.channel' && args.method === 'channel_fold') {
            const ids = args.args[0];
            const state = args.args[1] || args.kwargs.state;
            return this._mockMailChannelChannelFold(ids, state);
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
            const ids = args.args[0];
            const pinned = args.args[1] || args.kwargs.pinned;
            return this._mockMailChannelChannelPin(ids, pinned);
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
        if (args.model === 'mail.channel' && args.method === 'load_more_members') {
            const [channel_ids] = args.args;
            const { known_member_ids } = args.kwargs;
            return this._mockMailChannelLoadMoreMembers(channel_ids, known_member_ids);
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
        // res.users method
        if (args.model === 'res.users' && args.method === 'systray_get_activities') {
            return this._mockResUsersSystrayGetActivities();
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
        if (args.method === 'notify_cancel_by_type') {
            return this._mockMailThreadNotifyCancelByType(args.model, args.kwargs.notification_type);
        }
        return this._super(route, args);
    },
    /**
     * @override
     */
    mockWrite(model) {
        const initialTrackedFieldValuesByRecordId = this._mockMailThread_TrackPrepare(model);
        const mockWriteResult = this._super(...arguments);
        if (initialTrackedFieldValuesByRecordId) {
            this._mockMailThread_TrackFinalize(model, initialTrackedFieldValuesByRecordId);
        }
        return mockWriteResult;
    },

    //--------------------------------------------------------------------------
    // Private Mocked Routes
    //--------------------------------------------------------------------------

    /**
     * Simulates `activity_format` on `mail.activity`.
     *
     * @private
     * @param {number[]} ids
     * @returns {Object[]}
     */
    _mockMailActivityActivityFormat(ids) {
        let res = this.mockRead('mail.activity', [ids]);
        res = res.map(record => {
            if (record.mail_template_ids) {
                record.mail_template_ids = record.mail_template_ids.map(template_id => {
                    const template = this.getRecords('mail.template', [['id', '=', template_id]])[0];
                    return {
                        id: template.id,
                        name: template.name,
                    };
                });
            }
            return record;
        });
        return res;
    },

    /**
     * Simulates the `/mail/attachment/delete` route.
     *
     * @private
     * @param {integer} attachment_id
     */
    async _mockRouteMailAttachmentRemove(attachment_id) {
        this.pyEnv['bus.bus']._sendone(this.currentPartnerId, 'ir.attachment/delete', { id: attachment_id });
        return this.pyEnv['ir.attachment'].unlink([attachment_id]);
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
        const messages = this._mockMailMessage_MessageFetch(domain, max_id, min_id, limit);
        this._mockMailMessageSetMessageDone(messages.map(message => message.id));
        return this._mockMailMessageMessageFormat(messages.map(message => message.id));
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
        const mailChannel = this.getRecords('mail.channel', [['uuid', '=', uuid]])[0];
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
            const author = this.getRecords('res.users', [['id', '=', user_id]])[0];
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
        const messages = this._mockMailMessage_MessageFetch(domain, max_id, min_id, limit);
        return this._mockMailMessageMessageFormat(messages.map(message => message.id));
    },
    /**
     * Simulates the `/mail/inbox/messages` route.
     *
     * @private
     * @returns {Object}
     */
    _mockRouteMailMessageInbox(min_id = false, max_id = false, limit = 30) {
        const domain = [['needaction', '=', true]];
        const messages = this._mockMailMessage_MessageFetch(domain, max_id, min_id, limit);
        return this._mockMailMessageMessageFormat(messages.map(message => message.id));
    },
    /**
     * Simulates the `/mail/starred/messages` route.
     *
     * @private
     * @returns {Object}
     */
    _mockRouteMailMessageStarredMessages(min_id = false, max_id = false, limit = 30) {
        const domain = [['starred_partner_ids', 'in', [this.currentPartnerId]]];
        const messages = this._mockMailMessage_MessageFetch(domain, max_id, min_id, limit);
        return this._mockMailMessageMessageFormat(messages.map(message => message.id));
    },
    /**
     * Simulates the `/mail/read_subscription_data` route.
     *
     * @private
     * @param {integer} follower_id
     * @returns {Object[]} list of followed subtypes
     */
    async _mockRouteMailReadSubscriptionData(follower_id) {
        const follower = this.getRecords('mail.followers', [['id', '=', follower_id]])[0];
        const subtypes = this.getRecords('mail.message.subtype', [
            '&',
            ['hidden', '=', false],
            '|',
            ['res_model', '=', follower.res_model],
            ['res_model', '=', false],
        ]);
        const subtypes_list = subtypes.map(subtype => {
            const parent = this.getRecords('mail.message.subtype', [
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
     * Simulates the `/mail/thread/data` route.
     *
     * @param {string} thread_model
     * @param {integer} thread_id
     * @param {string[]} request_list
     * @returns {Object}
     */
    async _mockRouteMailThreadData(thread_model, thread_id, request_list) {
        const res = {
            'hasWriteAccess': true, // mimic user with write access by default
            'hasReadAccess': true,
        };
        const thread = this.pyEnv[thread_model].searchRead([['id', '=', thread_id]])[0];
        if (!thread) {
            res['hasReadAccess'] = false;
            return res;
        }
        if (request_list.includes('activities')) {
            const activities = this.pyEnv['mail.activity'].searchRead([['id', 'in', thread.activity_ids || []]]);
            res['activities'] = this._mockMailActivityActivityFormat(activities.map(activity => activity.id));
        }
        if (request_list.includes('attachments')) {
            const attachments = this.pyEnv['ir.attachment'].searchRead(
                [['res_id', '=', thread.id], ['res_model', '=', thread_model]],
            ); // order not done for simplicity
            res['attachments'] = this._mockIrAttachment_attachmentFormat(attachments.map(attachment => attachment.id));
            res['mainAttachment'] = thread.message_main_attachment_id ? [['insert-and-replace', { 'id': thread.message_main_attachment_id[0] }]] : [['clear']];
        }
        if (request_list.includes('followers')) {
            const followers = this.pyEnv['mail.followers'].searchRead([['id', 'in', thread.message_follower_ids || []]]);
            // search read returns many2one relations as an array [id, display_name].
            // But the original route does not. Thus, we need to change it now.
            followers.forEach(follower => follower.partner_id = follower.partner_id[0]);
            res['followers'] = followers;
        }
        if (request_list.includes('suggestedRecipients')) {
            res['suggestedRecipients'] = this._mockMailThread_MessageGetSuggestedRecipients(thread_model, [thread.id])[thread_id];
        }
        return res;
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
        const messages = this._mockMailMessage_MessageFetch(domain, max_id, min_id, limit);
        this._mockMailMessageSetMessageDone(messages.map(message => message.id));
        return this._mockMailMessageMessageFormat(messages.map(message => message.id));
    },

    //--------------------------------------------------------------------------
    // Private Mocked Methods
    //--------------------------------------------------------------------------

    /**
     * Simulates `_attachment_format` on `ir.attachment`.
     *
     * @private
     * @param {integer} ids
     * @returns {Object}
     */
    _mockIrAttachment_attachmentFormat(ids) {
        const attachments = this.mockRead('ir.attachment', [ids]);
        return attachments.map(attachment => {
            const res = {
                'checksum': attachment.checksum,
                'filename': attachment.name,
                'id': attachment.id,
                'mimetype': attachment.mimetype,
                'name': attachment.name,
            };
            res['originThread'] = [['insert', {
                'id': attachment.res_id,
                'model': attachment.res_model,
            }]];
            return res;
        });
    },
    /**
     * Simulates `register_as_main_attachment` on `ir.attachment`.
     *
     * @private
     * @param {integer} ids
     * @param {boolean} [force=true]
     * @returns {boolean} dummy value for mock server
     */
    _mockIrAttachmentRegisterAsMainAttachment(ids, force = true) {
        const [attachment] = this.getRecords('ir.attachment', [['id', 'in', ids]]);
        if (!attachment.res_model) {
            return true; // dummy value for mock server
        }
        if (!this.models[attachment.res_model].fields['message_main_attachment_id']) {
            return true; // dummy value for mock server
        }
        const [record] = this.pyEnv[attachment.res_model].searchRead([['id', '=', attachment.res_id]]);
        if (force || !record.message_main_attachment_id) {
            this.pyEnv[attachment.res_model].write(
                [record.id],
                { message_main_attachment_id: attachment.id },
            );
        }
        return true; // dummy value for mock server
    },
    /**
     * Simulates `_action_done` on `mail.activity`.
     *
     * @private
     * @param {string} model
     * @param {integer[]} ids
     * @returns {Object}
     */
    _mockMailActivityActionDone(ids) {
        const activities = this.getRecords('mail.activity', [['id', 'in', ids]]);
        this.mockUnlink('mail.activity', [activities.map(activity => activity.id)]);
    },
    /**
     * Simulates `action_feedback` on `mail.activity`.
     *
     * @private
     * @param {string} model
     * @param {integer[]} ids
     * @returns {Object}
     */
    _mockMailActivityActionFeedback(ids) {
        this._mockMailActivityActionDone(ids);
    },
    /**
     * Simulates `action_feedback_schedule_next` on `mail.activity`.
     *
     * @private
     * @param {string} model
     * @param {integer[]} ids
     * @returns {Object}
     */
    _mockMailActivityActionFeedbackScheduleNext(ids) {
        this._mockMailActivityActionDone(ids);
        return {
            name: 'Schedule an Activity',
            view_mode: 'form',
            res_model: 'mail.activity',
            views: [[false, 'form']],
            type: 'ir.actions.act_window',
        }
    },
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
        const records = this.getRecords(res_model, domain);

        const activityTypes = this.getRecords('mail.activity.type', []);
        const activityIds = _.pluck(records, 'activity_ids').flat();

        const groupedActivities = {};
        const resIdToDeadline = {};
        const groups = self.mockReadGroup('mail.activity', {
            domain: [['id', 'in', activityIds]],
            fields: ['res_id', 'activity_type_id', 'ids:array_agg(id)', 'date_deadline:min(date_deadline)'],
            groupby: ['res_id', 'activity_type_id'],
            lazy: false,
        });
        groups.forEach(function (group) {
            // mockReadGroup doesn't correctly return all asked fields
            const activites = self.getRecords('mail.activity', group.__domain);
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
            activity_types: activityTypes.map((type) => {
                let mailTemplates = [];
                if (type.mail_template_ids) {
                    mailTemplates = type.mail_template_ids.map((template_id) => {
                        const template = this.getRecords('mail.template', [['id', '=', template_id]])[0];
                        return {
                            id: template.id,
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
    _mockMailBaseModel_MailTrack(model, trackedFieldNamesToField, initialTrackedFieldValues, record) {
        const trackingValueIds = [];
        const changedFieldNames = [];
        for (const fname in trackedFieldNamesToField) {
            const initialValue = initialTrackedFieldValues[fname];
            const newValue = record[fname];
            if (initialValue !== newValue) {
                const tracking = this._mockMailTrackingValue_CreateTrackingValues(initialValue, newValue, fname, trackedFieldNamesToField[fname], model);
                if (tracking) {
                    trackingValueIds.push(tracking);
                }
                changedFieldNames.push(fname);
            }
        }
        return { changedFieldNames, trackingValueIds };
    },
    /**
     * Simulates `action_unfollow` on `mail.channel`.
     *
     * @private
     * @param {integer[]} ids
     */
    _mockMailChannelActionUnfollow(ids) {
        const channel = this.getRecords('mail.channel', [['id', 'in', ids]])[0];
        const [channelMember] = this.getRecords('mail.channel.member', [['channel_id', 'in', ids], ['partner_id', '=', this.currentPartnerId]]);
        if (!channelMember) {
            return true;
        }
        this.pyEnv['mail.channel'].write(
            [channel.id],
            {
                channel_member_ids: [[2, channelMember.id]],
            },
        );
        this.pyEnv['bus.bus']._sendone(this.currentPartner, 'mail.channel/leave', {
            'id': channel.id,
        });
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
     *
     * @private
     * @param {integer[]} ids
     * @param {integer[]} partner_ids
     */
    _mockMailChannelAddMembers(ids, partner_ids) {
        const [channel] = this.getRecords('mail.channel', [['id', 'in', ids]]);
        const partners = this.getRecords('res.partner', [['id', 'in', partner_ids]]);
        for (const partner of partners) {
            this.pyEnv['mail.channel.member'].create({
                channel_id: channel.id,
                partner_id: partner.id,
            });
            const body = `<div class="o_mail_notification">invited ${partner.name} to the channel</div>`;
            const message_type = "notification";
            const subtype_xmlid = "mail.mt_comment";
            this._mockMailChannelMessagePost(
                channel.id,
                { body, message_type, subtype_xmlid },
            );
        }
        this.pyEnv['bus.bus']._sendone(channel, 'mail.channel/joined', {
            'channel': this._mockMailChannelChannelInfo([channel.id])[0],
            'invited_by_user_id': this.currentUserId,
        });
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
        this.pyEnv['bus.bus']._sendmany(notifications);
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
            const user = this.getRecords('res.users', [['partner_id', 'in', partner_id]])[0];
            if (!user) {
                continue;
            }
            // Note: `channel_info` on the server is supposed to be called with
            // the proper user context but this is not done here for simplicity.
            const channelInfos = this._mockMailChannelChannelInfo(ids);
            const [relatedPartner] = this.pyEnv['res.partner'].searchRead([['id', '=', partner_id]]);
            for (const channelInfo of channelInfos) {
                notifications.push([relatedPartner, 'mail.channel/legacy_insert', channelInfo]);
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
        const channels = this.getRecords('mail.channel', [['id', 'in', ids]]);
        for (const channel of channels) {
            const channelMessages = this.getRecords('mail.message', [
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
            const [memberOfCurrentUser] = this.getRecords('mail.channel.member', [['channel_id', '=', channel.id], ['partner_id', '=', this.currentPartnerId]]);
            this.pyEnv['mail.channel.member'].write(
                [memberOfCurrentUser.id],
                { fetched_message_id: lastMessage.id },
            );
            this.pyEnv['bus.bus']._sendone(channel, 'mail.channel.member/fetched', {
                'channel_id': channel.id,
                'id': memberOfCurrentUser.id,
                'last_message_id': lastMessage.id,
                'partner_id': this.currentPartnerId,
            });
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
        const channels = this.getRecords('mail.channel', [['id', 'in', ids]]);
        return channels.map(channel => {
            const channelMessages = this.getRecords('mail.message', [
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
     * @param {number} ids
     * @param {state} [state]
     */
    _mockMailChannelChannelFold(ids, state) {
        const channels = this.getRecords('mail.channel', [['id', 'in', ids]]);
        for (const channel of channels) {
            const [memberOfCurrentUser] = this.getRecords('mail.channel.member', [['channel_id', '=', channel.id], ['partner_id', '=', this.currentPartnerId]]);
            const foldState = state ? state : memberOfCurrentUser.fold_state === 'open' ? 'folded' : 'open';
            const vals = {
                fold_state: foldState,
                is_minimized: foldState !== 'closed',
            };
            this.pyEnv['mail.channel.member'].write([memberOfCurrentUser.id], vals);
            this.pyEnv['bus.bus']._sendone(this.currentPartner, 'mail.channel/insert', {
                'id': channel.id,
                'serverFoldState': memberOfCurrentUser.fold_state,
            });
        }
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
        const partners = this.getRecords('res.partner', [['id', 'in', partners_to]]);
        // NOTE: this mock is not complete, which is done for simplicity.
        // Indeed if a chat already exists for the given partners, the server
        // is supposed to return this existing chat. But the mock is currently
        // always creating a new chat, because no test is relying on receiving
        // an existing chat.
        const id = this.pyEnv['mail.channel'].create({
            channel_member_ids: partners.map(partner => [0, 0, {
                partner_id: partner.id,
            }]),
            channel_type: 'chat',
            name: partners.map(partner => partner.name).join(", "),
            public: 'private',
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
        const channels = this.getRecords('mail.channel', [['id', 'in', ids]]);
        return channels.map(channel => {
            const members = this.getRecords('mail.channel.member', [['id', 'in', channel.channel_member_ids]]);
            const partnerIds = members.filter(member => member.partner_id).map(member => member.partner_id);
            const messages = this.getRecords('mail.message', [
                ['model', '=', 'mail.channel'],
                ['res_id', '=', channel.id],
            ]);
            const [group_public_id] = this.getRecords('res.groups', [
                ['id', '=', channel.group_public_id],
            ]);
            const lastMessageId = messages.reduce((lastMessageId, message) => {
                if (!lastMessageId || message.id > lastMessageId) {
                    return message.id;
                }
                return lastMessageId;
            }, undefined);
            const messageNeedactionCounter = this.getRecords('mail.notification', [
                ['res_partner_id', '=', this.currentPartnerId],
                ['is_read', '=', false],
                ['mail_message_id', 'in', messages.map(message => message.id)],
            ]).length;
            const channelData = {
                channel_type: channel.channel_type,
                id: channel.id,
            };
            const res = Object.assign({}, channel, {
                last_message_id: lastMessageId,
                members: [...this._mockResPartnerMailPartnerFormat(partnerIds).values()],
                message_needaction_counter: messageNeedactionCounter,
                authorizedGroupFullName: group_public_id ? group_public_id.name : false,
            });
            if (channel.channel_type === 'channel') {
                delete res.members;
            } else {
                res['seen_partners_info'] = members.filter(member => member.partner_id).map(member => {
                    return {
                        partner_id: member.partner_id,
                        seen_message_id: member.seen_message_id,
                        fetched_message_id: member.fetched_message_id,
                    };
                });
            }
            const [memberOfCurrentUser] = this.getRecords('mail.channel.member', [['channel_id', '=', channel.id], ['partner_id', '=', this.currentPartnerId]]);
            if (memberOfCurrentUser) {
                Object.assign(res, {
                    custom_channel_name: memberOfCurrentUser.custom_channel_name,
                    is_minimized: memberOfCurrentUser.is_minimized,
                    is_pinned: memberOfCurrentUser.is_pinned,
                    last_interest_dt: memberOfCurrentUser.last_interest_dt,
                    message_unread_counter: memberOfCurrentUser.message_unread_counter,
                    state: memberOfCurrentUser.fold_state || 'open',
                });
                if (memberOfCurrentUser.rtc_inviting_session_id) {
                    res['rtc_inviting_session'] = { 'id': memberOfCurrentUser.rtc_inviting_session_id };
                }
            }
            res.channel = [['insert-and-replace', channelData]];
            return res;
        });
    },
    /**
     * Simulates the `channel_pin` method of `mail.channel`.
     *
     * @private
     * @param {number[]} ids
     * @param {boolean} [pinned=false]
     */
    async _mockMailChannelChannelPin(ids, pinned = false) {
        const [channel] = this.getRecords('mail.channel', [['id', 'in', ids]]);
        const [memberOfCurrentUser] = this.getRecords('mail.channel.member', [['channel_id', '=', channel.id], ['partner_id', '=', this.currentPartnerId], ['is_pinned', '!=', pinned]]);
        if (memberOfCurrentUser) {
            this.pyEnv['mail.channel.member'].write(
                [memberOfCurrentUser.id],
                { is_pinned: pinned },
            );
        }
        if (!pinned) {
            this.pyEnv['bus.bus']._sendone(this.currentPartner, 'mail.channel/unpin', {
                'id': channel.id,
            });
        } else {
            this.pyEnv['bus.bus']._sendone(this.currentPartner, 'mail.channel/legacy_insert', this._mockMailChannelChannelInfo([channel.id])[0]);
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
        const channel = this.getRecords('mail.channel', [['id', '=', channel_id]])[0];
        const messagesBeforeGivenLastMessage = this.getRecords('mail.message', [
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
        const [memberOfCurrentUser] = this.getRecords('mail.channel.member', [['channel_id', '=', channel_id], ['partner_id', '=', this.currentPartnerId]]);
        if (memberOfCurrentUser.seen_message_id && memberOfCurrentUser.seen_message_id >= last_message_id) {
            return;
        }
        this._mockMailChannel_SetLastSeenMessage([channel.id], last_message_id);
        this.pyEnv['bus.bus']._sendone(channel.channel_type === 'chat' ? channel : this.currentPartner, 'mail.channel.member/seen', {
            'channel_id': channel.id,
            'last_message_id': last_message_id,
            'partner_id': this.currentPartnerId,
        });
    },
    /**
     * Simulates `channel_rename` on `mail.channel`.
     *
     * @private
     * @param {integer[]} ids
     */
    _mockMailChannelChannelRename(ids, name) {
        const channel = this.getRecords('mail.channel', [['id', 'in', ids]])[0];
        this.pyEnv['mail.channel'].write(
            [channel.id],
            { name },
        );
        this.pyEnv['bus.bus']._sendone(channel, 'mail.channel/insert', {
            'id': channel.id,
            'name': name,
        });
    },
    /**
     * Simulates `channel_set_custom_name` on `mail.channel`.
     *
     * @private
     * @param {integer[]} ids
     */
    _mockMailChannelChannelSetCustomName(ids, name) {
        const channelId = ids[0]; // simulate ensure_one.
        const [memberIdOfCurrentUser] = this.pyEnv['mail.channel.member'].search([['partner_id', '=', this.currentPartnerId], ['channel_id', '=', channelId]]);
        this.pyEnv['mail.channel.member'].write(
            [memberIdOfCurrentUser],
            { custom_channel_name: name },
        );
        this.pyEnv['bus.bus']._sendone(this.currentPartner, 'mail.channel/insert', {
            'id': channelId,
            'custom_channel_name': name,
        });
    },
    /**
     * Simulates the `create_group` on `mail.channel`.
     *
     * @private
     * @param {integer[]} partners_to
     * @returns {Object}
     */
    async _mockMailChannelCreateGroup(partners_to) {
        const partners = this.getRecords('res.partner', [['id', 'in', partners_to]]);
        const id = this.pyEnv['mail.channel'].create({
            channel_type: 'group',
            channel_member_ids: partners.map(partner => [0, 0, { partner_id: partner.id }]),
            name: '',
            public: 'private',
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
        const channel = this.getRecords('mail.channel', [['id', 'in', args.args[0]]])[0];
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
        const channels = this.getRecords('mail.channel', [['id', 'in', ids]]);
        for (const channel of channels) {
            const members = this.getRecords('mail.channel.member', [['id', 'in', channel.channel_member_ids]]);
            const otherPartnerIds = members.filter(member => member.partner_id && member.partner_id !== this.currentPartnerId).map(member => member.partner_id);
            const otherPartners = this.getRecords('res.partner', [['id', 'in', otherPartnerIds]]);
            let message = "You are alone in this channel.";
            if (otherPartners.length > 0) {
                message = `Users in this channel: ${otherPartners.map(partner => partner.name).join(', ')} and you`;
            }
            this.pyEnv['bus.bus']._sendone(this.currentPartner, 'mail.channel/transient_message', {
                'body': `<span class="o_mail_notification">${message}</span>`,
                'model': 'mail.channel',
                'res_id': channel.id,
            });
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

        const mentionSuggestions = mentionSuggestionsFilter(this.models['mail.channel'].records, search, limit);

        return mentionSuggestions;
    },
    /**
     * Simulates `write` on `mail.channel` when `image_128` changes.
     *
     * @param {integer} id
     */
    _mockMailChannelWriteImage128(id) {
        this.pyEnv['mail.channel'].write(
            [id],
            {
                avatarCacheKey: moment.utc().format("YYYYMMDDHHmmss"),
            },
        );
        const channel = this.pyEnv['mail.channel'].searchRead([['id', '=', id]])[0];
        this.pyEnv['bus.bus']._sendone(channel, 'mail.channel/insert', {
            'id': id,
            'avatarCacheKey': channel.avatarCacheKey
        });
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
        const channel = this.getRecords('mail.channel', [['id', '=', id]])[0];
        if (channel.channel_type !== 'channel') {
            const [memberOfCurrentUser] = this.getRecords('mail.channel.member', [['channel_id', '=', channel.id], ['partner_id', '=', this.currentPartnerId]]);
            this.pyEnv['mail.channel.member'].write(
                [memberOfCurrentUser.id],
                {
                    last_interest_dt: datetime_to_str(new Date()),
                    is_pinned: true,
                },
            );
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
        }
        // simulate compute of message_unread_counter
        const otherMembers = this.getRecords('mail.channel.member', [['channel_id', '=', channel.id], ['partner_id', '!=', this.currentPartnerId]]);
        for (const member of otherMembers) {
            this.pyEnv['mail.channel.member'].write(
                [member.id],
                { message_unread_counter: member.message_unread_counter + 1 },
            );
        }
        return messageData;
    },
    /**
     * Simulates `load_more_members` on `mail.channel`.
     *
     * @private
     * @param {integer[]} channel_ids
     * @param {integer[]} known_member_ids
     */
    _mockMailChannelLoadMoreMembers(channel_ids, known_member_ids) {
        const members = this.pyEnv['mail.channel.member'].searchRead([
            ['id', 'not in', known_member_ids],
            ['channel_id', 'in', channel_ids],
        ], { limit: 100 });
        const memberCount = this.pyEnv['mail.channel.member'].searchCount([
            ['channel_id', 'in', channel_ids],
        ]);
        const membersData = [];
        for (const member of members) {
            let persona;
            if (member.partner_id) {
                const [partner] = this.pyEnv['res.partner'].searchRead(
                    [['id', '=', member.partner_id[0]]],
                    { fields: ['id', 'name', 'im_status'] }
                );
                persona = {
                    'partner': [['insert-and-replace', {
                        'id': partner.id,
                        'name': partner.name,
                        'im_status': partner.im_status,
                    }]],
                };
            }
            if (member.guest_id) {
                const [guest] = this.pyEnv['mail.guest'].searchRead(
                    [['id', '=', member.guest_id[0]]],
                    { fields: ['id', 'name'] }
                );
                persona = {
                    'guest': [['insert-and-replace', {
                        'id': guest.id,
                        'name': guest.name,
                    }]],
                };
            }
            membersData.push({
                'id': member.id,
                'persona': [['insert-and-replace', persona]],
            });
        }
        return {
            channelMembers: [['insert', membersData]],
            memberCount,
        };
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
        const channels = this.getRecords('mail.channel', [['id', 'in', ids]]);
        let partner_id;
        if ('mockedPartnerId' in context) {
            partner_id = context.mockedPartnerId;
        } else {
            partner_id = this.currentPartnerId;
        }
        const partner = this.getRecords('res.partner', [['id', '=', partner_id]]);
        const notifications = [];
        for (const channel of channels) {
            const data = [channel, 'mail.channel.member/typing_status', {
                'channel_id': channel.id,
                'is_typing': is_typing,
                'partner_id': partner_id,
                'partner_name': partner.name,
            }];
            notifications.push(data);
        }
        this.pyEnv['bus.bus']._sendmany(notifications);
    },
    /**
     * Simulates the `_set_last_seen_message` method of `mail.channel`.
     *
     * @private
     * @param {integer[]} ids
     * @param {integer} message_id
     */
    _mockMailChannel_SetLastSeenMessage(ids, message_id) {
        const [memberOfCurrentUser] = this.getRecords('mail.channel.member', [['channel_id', 'in', ids], ['partner_id', '=', this.currentPartnerId]]);
        this.pyEnv['mail.channel.member'].write([memberOfCurrentUser.id], {
            fetched_message_id: message_id,
            seen_message_id: message_id,
        });
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
            const messages = this.getRecords('mail.message', domain);
            const ids = messages.map(messages => messages.id);
            this._mockMailMessageSetMessageDone(ids);
            return ids;
        }
        const notifications = this.getRecords('mail.notification', notifDomain);
        this.pyEnv['mail.notification'].write(
            notifications.map(notification => notification.id),
            { is_read: true },
        );
        const messageIds = [];
        for (const notification of notifications) {
            if (!messageIds.includes(notification.mail_message_id)) {
                messageIds.push(notification.mail_message_id);
            }
        }
        const messages = this.getRecords('mail.message', [['id', 'in', messageIds]]);
        // simulate compute that should be done based on notifications
        for (const message of messages) {
            this.pyEnv['mail.message'].write(
                [message.id],
                {
                    needaction: false,
                    needaction_partner_ids: message.needaction_partner_ids.filter(
                        partnerId => partnerId !== this.currentPartnerId
                    ),
                },
            );
        }
        this.pyEnv['bus.bus']._sendone(this.currentPartner, 'mail.message/mark_as_read', {
            'message_ids': messageIds,
            'needaction_inbox_counter': this._mockResPartner_GetNeedactionCount(this.currentPartnerId),
        });
        return messageIds;
    },
    /**
     * Simulates `_message_fetch` on `mail.message`.
     *
     * @private
     * @param {Array[]} domain
     * @param {integer} [max_id]
     * @param {integer} [min_id]
     * @param {integer} [limit=30]
     * @returns {Object[]}
     */
    _mockMailMessage_MessageFetch(domain, max_id, min_id, limit = 30) {
        if (max_id) {
            domain.push(['id', '<', max_id]);
        }
        if (min_id) {
            domain.push(['id', '>', min_id]);
        }
        let messages = this.getRecords('mail.message', domain);
        // sorted from highest ID to lowest ID (i.e. from youngest to oldest)
        messages.sort(function (m1, m2) {
            return m1.id < m2.id ? 1 : -1;
        });
        // pick at most 'limit' messages
        messages.length = Math.min(messages.length, limit);
        return messages;
    },
    /**
     * Simulates `message_format` on `mail.message`.
     *
     * @private
     * @returns {integer[]} ids
     * @returns {Object[]}
     */
    _mockMailMessageMessageFormat(ids) {
        const messages = this.getRecords('mail.message', [['id', 'in', ids]]);
        // sorted from highest ID to lowest ID (i.e. from most to least recent)
        messages.sort(function (m1, m2) {
            return m1.id < m2.id ? 1 : -1;
        });
        return messages.map(message => {
            const thread = message.model && this.getRecords(message.model, [
                ['id', '=', message.res_id],
            ])[0];
            let formattedAuthor;
            if (message.author_id) {
                const author = this.getRecords(
                    'res.partner',
                    [['id', '=', message.author_id]],
                    { active_test: false }
                )[0];
                formattedAuthor = [author.id, author.display_name];
            } else {
                formattedAuthor = [0, message.email_from];
            }
            const attachments = this.getRecords('ir.attachment', [
                ['id', 'in', message.attachment_ids],
            ]);
            const formattedAttachments = [['insert-and-replace', this._mockIrAttachment_attachmentFormat(attachments.map(attachment => attachment.id))]];
            const allNotifications = this.getRecords('mail.notification', [
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
            const trackingValueIds = this.getRecords('mail.tracking.value', [
                ['id', 'in', message.tracking_value_ids],
            ]);
            const formattedTrackingValues = [['insert-and-replace', this._mockMailTrackingValue_TrackingValueFormat(trackingValueIds)]];
            const partners = this.getRecords(
                'res.partner',
                [['id', 'in', message.partner_ids]],
            );
            const response = Object.assign({}, message, {
                attachment_ids: formattedAttachments,
                author_id: formattedAuthor,
                history_partner_ids: historyPartnerIds,
                needaction_partner_ids: needactionPartnerIds,
                notifications,
                parentMessage: message.parent_id ? this._mockMailMessageMessageFormat([message.parent_id])[0] : false,
                recipients: partners.map(p => ({ id: p.id, name: p.name })),
                record_name: thread && (thread.name !== undefined ? thread.name : thread.display_name),
                trackingValues: formattedTrackingValues,
            });
            if (message.subtype_id) {
                const subtype = this.getRecords('mail.message.subtype', [
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
        const messages = this.getRecords('mail.message', [['id', 'in', ids]]);
        return messages.map(message => {
            let notifications = this.getRecords('mail.notification', [
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
        const messages = this.getRecords('mail.message', [['id', 'in', ids]]);

        const notifications = this.getRecords('mail.notification', [
            ['res_partner_id', '=', this.currentPartnerId],
            ['is_read', '=', false],
            ['mail_message_id', 'in', messages.map(messages => messages.id)]
        ]);
        this.pyEnv['mail.notification'].write(
            notifications.map(notification => notification.id),
            { is_read: true },
        );
        // simulate compute that should be done based on notifications
        for (const message of messages) {
            this.pyEnv['mail.message'].write(
                [message.id],
                {
                    needaction: false,
                    needaction_partner_ids: message.needaction_partner_ids.filter(
                        partnerId => partnerId !== this.currentPartnerId
                    ),
                },
            );
            this.pyEnv['bus.bus']._sendone(this.currentPartner, 'mail.message/mark_as_read', {
                'message_ids': [message.id],
                'needaction_inbox_counter': this._mockResPartner_GetNeedactionCount(this.currentPartnerId),
            });
        }
    },
    /**
     * Simulates `toggle_message_starred` on `mail.message`.
     *
     * @private
     * @returns {integer[]} ids
     */
    _mockMailMessageToggleMessageStarred(ids) {
        const messages = this.getRecords('mail.message', [['id', 'in', ids]]);
        for (const message of messages) {
            const wasStared = message.starred_partner_ids.includes(this.currentPartnerId);
            this.pyEnv['mail.message'].write(
                [message.id],
                { starred_partner_ids: [[wasStared ? 3 : 4, this.currentPartnerId]] }
            );
            this.pyEnv['bus.bus']._sendone(this.currentPartner, 'mail.message/toggle_star', {
                'message_ids': [message.id],
                'starred': !wasStared,
            });
        }
    },
    /**
     * Simulates `unstar_all` on `mail.message`.
     *
     * @private
     */
    _mockMailMessageUnstarAll() {
        const messages = this.getRecords('mail.message', [
            ['starred_partner_ids', 'in', this.currentPartnerId],
        ]);
        this.pyEnv['mail.message'].write(
            messages.map(message => message.id),
            { starred_partner_ids: [[3, this.currentPartnerId]] }
        );
        this.pyEnv['bus.bus']._sendone(this.currentPartner, 'mail.message/toggle_star', {
            'message_ids': messages.map(message => message.id),
            'starred': false,
        });
    },
    /**
     * Simulates `_filtered_for_web_client` on `mail.notification`.
     *
     * @private
     * @returns {integer[]} ids
     * @returns {Object[]}
     */
    _mockMailNotification_FilteredForWebClient(ids) {
        const notifications = this.getRecords('mail.notification', [
            ['id', 'in', ids],
        ]);
        return notifications.filter(notification => {
            const partner = this.getRecords('res.partner', [['id', '=', notification.res_partner_id]])[0];
            if (['bounce', 'exception', 'canceled'].includes(notification.notification_status) ||
                (partner && partner.partner_share)) {
                return true;
            }
            const message = this.getRecords('mail.message', [['id', '=', notification.mail_message_id]])[0];
            const subtypes = (message.subtype_id) ?
                this.getRecords('mail.message.subtype', [['id', '=', message.subtype_id]]) : [];
            return (subtypes.length == 0) || subtypes[0].track_recipients;
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
        const notifications = this.getRecords('mail.notification', [['id', 'in', ids]]);
        return notifications.map(notification => {
            const partner = this.getRecords('res.partner', [['id', '=', notification.res_partner_id]])[0];
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
            const user = this.getRecords(
                'res.users',
                [['id', '=', user_id]],
                { active_test: false },
            )[0];
            const author = this.getRecords(
                'res.partner',
                [['id', '=', user.partner_id]],
                { active_test: false },
            )[0];
            author_id = author.id;
            email_from = `${author.display_name} <${author.email}>`;
        }

        if (email_from === undefined) {
            if (author_id) {
                const author = this.getRecords(
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
        const record = this.getRecords(model, [['id', 'in', 'ids']])[0];
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
        if (model === 'res.fake') {
            return this._mockResFake_MessageGetSuggestedRecipients(model, ids);
        }
        const result = ids.reduce((result, id) => result[id] = [], {});
        const records = this.getRecords(model, [['id', 'in', ids]]);
        for (const record in records) {
            if (record.user_id) {
                const user = this.getRecords('res.users', [['id', '=', record.user_id]]);
                if (user.partner_id) {
                    const reason = this.models[model].fields['user_id'].string;
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
        const records = this.getRecords(model, [['id', 'in', ids]]);

        for (const record of records) {
            result[record.id] = [];
            if (record.email_cc) {
                result[record.id].push([
                    false,
                    record.email_cc,
                    undefined,
                    'CC email',
                ]);
            }
            const partners = this.getRecords(
                'res.partner',
                [['id', 'in', record.partner_ids]],
            );
            if (partners.length) {
                for (const partner of partners) {
                    result[record.id].push([
                        partner.id,
                        partner.display_name,
                        undefined,
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
            const attachments = this.getRecords('ir.attachment', [
                ['id', 'in', kwargs.attachment_ids],
                ['res_model', '=', 'mail.compose.message'],
                ['res_id', '=', 0],
            ]);
            const attachmentIds = attachments.map(attachment => attachment.id);
            this.pyEnv['ir.attachment'].write(
                attachmentIds,
                {
                    res_id: id,
                    res_model: model,
                },
            );
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
        const messageId = this.pyEnv['mail.message'].create(values);
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
        for (const id of ids) {
            for (const partner_id of partner_ids) {
                const followerId = this.pyEnv['mail.followers'].create({
                    is_active: true,
                    partner_id,
                    res_id: id,
                    res_model: model,
                    subtype_ids: subtype_ids,
                });
                this.pyEnv['res.partner'].write([partner_id], {
                    message_follower_ids: [followerId],
                });
            }
        }
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
        const message = this.getRecords('mail.message', [['id', '=', messageId]])[0];
        const messageFormat = this._mockMailMessageMessageFormat([messageId])[0];
        const notifications = [];
        if (model === 'mail.channel') {
            // members
            const channels = this.getRecords('mail.channel', [['id', '=', message.res_id]]);
            for (const channel of channels) {
                notifications.push([channel, 'mail.channel/new_message', {
                    'id': channel.id,
                    'message': messageFormat,
                }]);
                // notify update of last_interest_dt
                const now = datetime_to_str(new Date());
                const members = this.getRecords('mail.channel.member', [['id', 'in', channel.channel_member_ids]]);
                this.pyEnv['mail.channel.member'].write(
                    members.map(member => member.id),
                    { last_interest_dt: now },
                );
                for (const member of members) {
                    // simplification, send everything on the current user "test" bus, but it should send to each member instead
                    notifications.push([member, 'mail.channel/last_interest_dt_changed', {
                        'id': channel.id,
                        'last_interest_dt': member.last_interest_dt,
                    }]);
                }
            }
        }
        this.pyEnv['bus.bus']._sendmany(notifications);
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
        const followers = this.getRecords('mail.followers', [
            ['res_model', '=', model],
            ['res_id', 'in', ids],
            ['partner_id', 'in', partner_ids || []],
        ]);
        this.pyEnv['mail.followers'].unlink(followers.map(follower => follower.id));
    },
    /**
     * Simulates `_message_track` on `mail.thread`
     */
    _mockMailThread_MessageTrack(modelName, trackedFieldNames, initialTrackedFieldValuesByRecordId) {
        const trackFieldNamesToField = this.mockFieldsGet(modelName, [trackedFieldNames]);
        const tracking = {};
        const records = this.models[modelName].records;
        for (const record of records) {
            tracking[record.id] = this._mockMailBaseModel_MailTrack(modelName, trackFieldNamesToField, initialTrackedFieldValuesByRecordId[record.id], record);
        }
        for (const record of records) {
            const { trackingValueIds, changedFieldNames } = tracking[record.id] || {};
            if (!changedFieldNames || !changedFieldNames.length) {
                continue;
            }
            const changedFieldsInitialValues = {};
            const initialFieldValues = initialTrackedFieldValuesByRecordId[record.id];
            for (const fname in changedFieldNames) {
                changedFieldsInitialValues[fname] = initialFieldValues[fname];
            }
            const subtype = this._mockMailThread_TrackSubtype(changedFieldsInitialValues);
            this._mockMailThreadMessagePost(modelName, [record.id], {
                subtype_id: subtype.id,
                tracking_value_ids: trackingValueIds,
            });
        }
        return tracking;
    },
    /**
     * Simulates `_track_finalize` on `mail.thread`
     */
    _mockMailThread_TrackFinalize(model, initialTrackedFieldValuesByRecordId) {
        this._mockMailThread_MessageTrack(
            model,
            this._mockMailThread_TrackGetFields(model),
            initialTrackedFieldValuesByRecordId,
        );
    },
    /**
     * Simulates `_track_get_fields` on `mail.thread`
     */
    _mockMailThread_TrackGetFields(model) {
        return Object.entries(this.models[model].fields).reduce((prev, next) => {
            if (next[1].tracking) {
                prev.push(next[0]);
            }
            return prev;
        }, []);
    },
    /**
     * Simulates `_track_prepare` on `mail.thread`
     */
    _mockMailThread_TrackPrepare(model) {
        const trackedFieldNames = this._mockMailThread_TrackGetFields(model);
        if (!trackedFieldNames.length) {
            return;
        }
        const initialTrackedFieldValuesByRecordId = {};
        for (const record of this.models[model].records) {
            const values = {};
            initialTrackedFieldValuesByRecordId[record.id] = values;
            for (const fname of trackedFieldNames) {
                values[fname] = record[fname];
            }
        }
        return initialTrackedFieldValuesByRecordId;
    },
    /**
     * Simulates `_track_subtype` on `mail.thread`
     */
    _mockMailThread_TrackSubtype(initialFieldValuesByRecordId) {
        return false;
    },
    /**
     * Simulates `create_tracking_values` on `mail.tracking.value`
     */
     _mockMailTrackingValue_CreateTrackingValues(initialValue, newValue, fieldName, field, modelName) {
        let isTracked = true;
        const irField = this.models['ir.model.fields'].records.find(field => field.model === modelName && field.name === fieldName);

        if (!irField) {
            return;
        }

        const values = { field: irField['id'], field_desc: field['string'], field_type: field['type'] };
        switch (values.field_type) {
            case 'char':
            case 'datetime':
            case 'float':
            case 'integer':
            case 'monetary':
            case 'text':
                values[`old_value_${values.field_type}`] = initialValue;
                values[`new_value_${values.field_type}`] = newValue;
                break;
            case 'date':
                values['old_value_datetime'] = initialValue;
                values['new_value_datetime'] = newValue;
                break;
            case 'boolean':
                values['old_value_integer'] = initialValue ? 1 : 0;
                values['new_value_integer'] = newValue ? 1 : 0;
                break;
            case 'selection':
                values['old_value_char'] = initialValue;
                values['new_value_char'] = newValue;
                break;
            case 'many2one':
                initialValue = initialValue ? this.pyEnv[field.relation].searchRead([['id', '=', initialValue]])[0] : initialValue;
                newValue = newValue ? this.pyEnv[field.relation].searchRead([['id', '=', newValue]])[0] : newValue;
                values['old_value_integer'] = initialValue ? initialValue.id : 0;
                values['new_value_integer'] = newValue ? newValue.id : 0;
                values['old_value_char'] = initialValue ? initialValue.display_name : '';
                values['new_value_char'] = newValue ? newValue.display_name : '';
                break;
            default:
                isTracked = false;
        }
        if (isTracked) {
            return this.pyEnv['mail.tracking.value'].create(values);
        }
        return false;
    },
    /**
     * Simulates `_tracking_value_format` on `mail.tracking.value`
     */
    _mockMailTrackingValue_TrackingValueFormat(tracking_value_ids) {
        const trackingValues = tracking_value_ids.map(tracking => ({
            changedField: tracking.field_desc,
            id: tracking.id,
            newValue: [['insert-and-replace', {
                fieldType: tracking.field_type,
                value: this._mockMailTrackingValue_GetDisplayValue(tracking, 'new')
            }]],
            oldValue: [['insert-and-replace', {
                fieldType: tracking.field_type,
                value: this._mockMailTrackingValue_GetDisplayValue(tracking, 'old')
            }]],
        }));
        return trackingValues;
    },
    /**
     * Simulates `_get_display_value` on `mail.tracking.value`
     */
    _mockMailTrackingValue_GetDisplayValue(record, type) {
        switch (record.field_type) {
            case 'float':
            case 'integer':
            case 'monetary':
            case 'text':
                return record[`${type}_value_${record.field_type}`];
            case 'datetime':
                if (record[`${type}_value_datetime`]) {
                    const datetime = record[`${type}_value_datetime`];
                    return `${datetime}Z`;
                } else {
                    return record[`${type}_value_datetime`];
                }
            case 'date':
                if (record[`${type}_value_datetime`]) {
                    return record[`${type}_value_datetime`];
                } else {
                    return record[`${type}_value_datetime`];
                }
            case 'boolean':
                return !!record[`${type}_value_integer`];
            default:
                return record[`${type}_value_char`];
        }
    },
    /**
     * Simulates `_get_channels_as_member` on `res.partner`.
     *
     * @private
     * @param {integer[]} ids
     * @returns {Object}
     */
    _mockResPartner_GetChannelsAsMember(ids) {
        const partner = this.getRecords('res.partner', [['id', 'in', ids]])[0];
        const channelMembers = this.getRecords('mail.channel.member', [['partner_id', '=', partner.id]]);
        const channels = this.getRecords('mail.channel', [
            ['channel_type', 'in', ['channel', 'group']],
            ['channel_member_ids', 'in', channelMembers.map(member => member.id)],
        ]);
        const directMessagesMembers = this.getRecords('mail.channel.member', [['partner_id', '=', partner.id], ['is_pinned', '=', true]]);
        const directMessages = this.getRecords('mail.channel', [
            ['channel_type', '=', 'chat'],
            ['channel_member_ids', 'in', directMessagesMembers.map(member => member.id)],
        ]);
        return [
            ...channels,
            ...directMessages,
        ];
    },
    /**
     * Simulates `systray_get_activities` on `res.users`.
     *
     * @private
     */
     _mockResUsersSystrayGetActivities() {
        const activities = this.pyEnv['mail.activity'].searchRead([]);
        const userActivitiesByModelName = {};
        for (const activity of activities) {
            const today = date_to_str(new Date());
            if (today === activity['date_deadline']) {
                activity['states'] = 'today';
            } else if (today > activity['date_deadline']) {
                activity['states'] = 'overdue';
            } else {
                activity['states'] = 'planned';
            }
        }
        for (const activity of activities) {
            const modelName = activity['res_model'];
            if (!userActivitiesByModelName[modelName]) {
                userActivitiesByModelName[modelName] = {
                    id: modelName, // for simplicity
                    model: modelName,
                    name: modelName,
                    overdue_count: 0,
                    planned_count: 0,
                    today_count: 0,
                    total_count: 0,
                    type: 'activity',
                };
            }
            userActivitiesByModelName[modelName][`${activity['states']}_count`] += 1;
            userActivitiesByModelName[modelName]['total_count'] += 1;
            userActivitiesByModelName[modelName].actions = [{
                icon: 'fa-clock-o',
                name: 'Summary',
            }];
        }
        return Object.values(userActivitiesByModelName);
    },
    /**
     * Simulates `_find_or_create_for_user` on `res.users.settings`.
     *
     * @param {Object} user
     * @returns {Object}
     */
    _mockResUsersSettings_FindOrCreateForUser(user_id) {
        let settings = this.getRecords('res.users.settings', [['user_id', '=', user_id]])[0];
        if (!settings) {
            const settingsId = this.pyEnv['res.users.settings'].create({ user_id: user_id });
            settings = this.getRecords('res.users.settings', [['id', '=', settingsId]])[0];
        }
        return settings;
    },

    /**
     * @param {integer} id
     * @param {string[]} [fieldsToFormat]
     * @returns {Object}
     */
    _mockResUsersSettings_ResUsersSettingsFormat(id, fieldsToFormat) {
        const [settings] = this.getRecords('res.users.settings', [['id', '=', id]]);
        const ormAutomaticFields = new Set(['create_date', 'create_uid', 'display_name', 'name', 'write_date', 'write_uid', '__last_update']);
        const filterPredicate = fieldsToFormat ? ([fieldName]) => fieldsToFormat.includes(fieldName) : ([fieldName]) => !ormAutomaticFields.has(fieldName);
        const res = Object.fromEntries(Object.entries(settings).filter(filterPredicate));
        if (Object.prototype.hasOwnProperty.call(res, 'user_id')) {
            res.user_id = [['insert-and-replace', { id: settings.user_id }]];
        }
        if (Object.prototype.hasOwnProperty.call(res, 'volume_settings_ids')) {
            const volumeSettings = this._mockResUsersSettingsVolumes_DiscussUsersSettingsVolumeFormat(settings.volume_settings_ids);
            res.volume_settings_ids = [['insert', volumeSettings]];
        }
        return res;
    },

    /**
     * Simulates `set_res_users_settings` on `res.users.settings`.
     *
     * @param {integer} id
     * @param {Object} newSettings
     */
    _mockResUsersSettingsSetResUsersSettings(id, newSettings) {
        const oldSettings = this.getRecords('res.users.settings', [['id', '=', id]])[0];
        const changedSettings = {};
        for (const setting in newSettings) {
            if (setting in oldSettings && newSettings[setting] !== oldSettings[setting]) {
                changedSettings[setting] = newSettings[setting];
            }
        }
        this.pyEnv['res.users.settings'].write(
            [id],
            changedSettings,
        );
        const [relatedUser] = this.pyEnv['res.users'].searchRead([['id', '=', oldSettings.user_id]]);
        const [relatedPartner] = this.pyEnv['res.partner'].searchRead([['id', '=', relatedUser.partner_id]]);
        this.pyEnv['bus.bus']._sendone(relatedPartner, 'res.users.settings/insert', { ...changedSettings, id });
    },

    _mockResUsersSettingsVolumes_DiscussUsersSettingsVolumeFormat(ids) {
        const volumeSettingsRecords = this.getRecords('res.users.settings.volumes', [['id', 'in', ids]]);
        return volumeSettingsRecords.map(volumeSettingsRecord => {
            const [relatedGuest] = this.getRecords('mail.guest', [['id', '=', volumeSettingsRecord.guest_id]]);
            const [relatedPartner] = this.getRecords('res.partner', [['id', '=', volumeSettingsRecord.partner_id]]);
            return {
                guest_id: relatedGuest ? [['insert-and-replace', { id: relatedGuest.id, name: relatedGuest.name }]] : [['clear']],
                id: volumeSettingsRecord.id,
                partner_id: relatedPartner ? [['insert-and-replace', { id: relatedPartner.id, name: relatedPartner.name }]] : [['clear']],
                volume: volumeSettingsRecord.volume,
            };
        });
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
        const partnersFromUsers = this.getRecords('res.users', [])
            .map(user => this.getRecords('res.partner', [['id', '=', user.partner_id]])[0])
            .filter(partner => partner);
        const mainMatchingPartners = mentionSuggestionsFilter(partnersFromUsers, search, limit);

        let extraMatchingPartners = [];
        // if not enough results add extra suggestions based on partners
        const remainingLimit = limit - mainMatchingPartners.length;
        if (mainMatchingPartners.length < limit) {
            const partners = this.getRecords('res.partner', [['id', 'not in', mainMatchingPartners.map(partner => partner.id)]]);
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
        const partner = this.getRecords('res.partner', [['id', '=', id]])[0];
        return this.getRecords('mail.notification', [
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
        const matchingPartners = this.getRecords('res.users', [])
            .filter(user => {
                const partner = this.getRecords('res.partner', [['id', '=', user.partner_id]])[0];
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
                const partner = this.getRecords('res.partner', [['id', '=', user.partner_id]])[0];
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
        const partners = this.getRecords(
            'res.partner',
            [['id', 'in', ids]],
            { active_test: false }
        );
        // Servers is also returning `is_internal_user` but not
        // done here for simplification.
        return new Map(partners.map(partner => {
            const users = this.getRecords('res.users', [['id', 'in', partner.user_ids]]);
            const internalUsers = users.filter(user => !user.share);
            let mainUser;
            if (internalUsers.length > 0) {
                mainUser = internalUsers[0];
            } else if (users.length > 0) {
                mainUser = users[0];
            } else {
                mainUser = [];
            }
            return [partner.id, {
                "active": partner.active,
                "display_name": partner.display_name,
                "email": partner.email,
                "id": partner.id,
                "im_status": partner.im_status,
                "name": partner.name,
                "user_id": mainUser.id,
            }];
        }));
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
            this.getRecords('res.users', [])
            .filter(user => {
                const partner = this.getRecords('res.partner', [['id', '=', user.partner_id]])[0];
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
        const partner = this.getRecords('res.partner', [['id', '=', id]])[0];
        const messages = this.getRecords('mail.message', [
            ['author_id', '=', partner.id],
            ['res_id', '!=', 0],
            ['model', '!=', false],
            ['message_type', '!=', 'user_notification'],
        ]).filter(message => {
            // Purpose is to simulate the following domain on mail.message:
            // ['notification_ids.notification_status', 'in', ['bounce', 'exception']],
            // But it's not supported by getRecords domain to follow a relation.
            const notifications = this.getRecords('mail.notification', [
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
        const user = this.getRecords('res.users', [['id', 'in', ids]])[0];
        const userSettings = this._mockResUsersSettings_FindOrCreateForUser(user.id);
        return {
            channels: this._mockMailChannelChannelInfo(this._mockResPartner_GetChannelsAsMember(user.partner_id).map(channel => channel.id)),
            current_partner: this._mockResPartnerMailPartnerFormat(user.partner_id).get(user.partner_id),
            current_user_id: this.currentUserId,
            current_user_settings: this._mockResUsersSettings_ResUsersSettingsFormat(userSettings.id),
            menu_id: false, // not useful in QUnit tests
            needaction_inbox_counter: this._mockResPartner_GetNeedactionCount(user.partner_id),
            partner_root: this._mockResPartnerMailPartnerFormat(this.partnerRootId).get(this.partnerRootId),
            publicPartners: [['insert', [{ 'id': this.publicPartnerId }]]],
            shortcodes: this.pyEnv['mail.shortcode'].searchRead([], { fields: ['source', 'substitution'] }),
            starred_counter: this.getRecords('mail.message', [['starred_partner_ids', 'in', user.partner_id]]).length,
        };
    },
    /**
     * Simulate the `notify_cancel_by_type` on `mail.thread` .
     * Note that this method is overridden by snailmail module but not simulated here.
     */
    _mockMailThreadNotifyCancelByType(model, notificationType) {
        // Query matching notifications
        const notifications = this.getRecords('mail.notification', [
            ['notification_type', '=', notificationType],
            ['notification_status', 'in', ['bounce', 'exception']],
        ]).filter(notification => {
            const message = this.getRecords('mail.message', [['id', '=', notification.mail_message_id]])[0];
            return message.model === model && message.author_id === this.currentPartnerId;
        });
        // Update notification status
        this.pyEnv['mail.notification'].write(
            notifications.map(notification => notification.id),
            { notification_status: 'canceled' },
        );
        // Send bus notifications to update status of notifications in the web client
        this.pyEnv['bus.bus']._sendone(this.currentPartner, 'mail.message/notification_update', {
            'elements': this._mockMailMessage_MessageNotificationFormat(
                notifications.map(notification => notification.mail_message_id)
            ),
        });
    },
});
