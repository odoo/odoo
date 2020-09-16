odoo.define('mail/static/src/models/messaging_notification_handler/messaging_notification_handler.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { one2one } = require('mail/static/src/model/model_field_utils.js');

const PREVIEW_MSG_MAX_SIZE = 350; // optimal for native English speakers

function factory(dependencies) {

    class MessagingNotificationHandler extends dependencies['mail.model'] {

        /**
         * @override
         */
        _willDelete() {
            this.env.services['bus_service'].off('notification');
            this.env.services['bus_service'].stopPolling();
            return super._willDelete(...arguments);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Fetch messaging data initially to populate the store specifically for
         * the current users. This includes pinned channels for instance.
         */
        start() {
            this.env.services.bus_service.onNotification(null, notifs => this._handleNotifications(notifs));
            this.env.services.bus_service.startPolling();
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @param {Object[]} notifications
         * @returns {Object[]}
         */
        _filterNotificationsOnUnsubscribe(notifications) {
            const unsubscribedNotif = notifications.find(notif =>
                notif[1].info === 'unsubscribe');
            if (unsubscribedNotif) {
                notifications = notifications.filter(notif =>
                    notif[0][1] !== 'mail.channel' ||
                    notif[0][2] !== unsubscribedNotif[1].id
                );
            }
            return notifications;
        }

        /**
         * @private
         * @param {Object[]} notifications
         * @param {Array|string} notifications[i][0] meta-data of the notification.
         * @param {string} notifications[i][0][0] name of database this
         *   notification comes from.
         * @param {string} notifications[i][0][1] type of notification.
         * @param {integer} notifications[i][0][2] usually id of related type
         *   of notification. For instance, with `mail.channel`, this is the id
         *   of the channel.
         * @param {Object} notifications[i][1] payload of the notification
         */
        async _handleNotifications(notifications) {
            const filteredNotifications = this._filterNotificationsOnUnsubscribe(notifications);
            const proms = filteredNotifications.map(notification => {
                const [channel, message] = notification;
                if (typeof channel === 'string') {
                    // uuid notification, only for (livechat) public handler
                    return;
                }
                const [, model, id] = channel;
                switch (model) {
                    case 'ir.needaction':
                        return this._handleNotificationNeedaction(message);
                    case 'mail.channel':
                        return this._handleNotificationChannel(id, message);
                    case 'res.partner':
                        if (id !== this.env.messaging.__mfield_currentPartner(this).__mfield_id(this)) {
                            // ignore broadcast to other partners
                            return;
                        }
                        return this._handleNotificationPartner(Object.assign({}, message));
                    default:
                        console.warn(`mail.messaging_notification_handler: Unhandled notification "${model}"`);
                        return;
                }
            });
            await this.async(() => Promise.all(proms));
        }

        /**
         * @private
         * @param {integer} channelId
         * @param {Object} data
         * @param {string} [data.info]
         * @param {boolean} [data.is_typing]
         * @param {integer} [data.last_message_id]
         * @param {integer} [data.partner_id]
         */
        async _handleNotificationChannel(channelId, data) {
            const {
                info,
                is_typing,
                last_message_id,
                partner_id,
            } = data;
            switch (info) {
                case 'channel_fetched':
                    return this._handleNotificationChannelFetched(channelId, {
                        last_message_id,
                        partner_id,
                    });
                case 'channel_seen':
                    return this._handleNotificationChannelSeen(channelId, {
                        last_message_id,
                        partner_id,
                    });
                case 'typing_status':
                    return this._handleNotificationChannelTypingStatus(channelId, {
                        is_typing,
                        partner_id,
                    });
                default:
                    return this._handleNotificationChannelMessage(channelId, data);
            }
        }

        /**
         * @private
         * @param {integer} channelId
         * @param {Object} param1
         * @param {integer} param1.last_message_id
         * @param {integer} param1.partner_id
         */
        async _handleNotificationChannelFetched(channelId, {
            last_message_id,
            partner_id,
        }) {
            const channel = this.env.models['mail.thread'].findFromIdentifyingData({
                __mfield_id: channelId,
                __mfield_model: 'mail.channel',
            });
            if (!channel) {
                // for example seen from another browser, the current one has no
                // knowledge of the channel
                return;
            }
            if (channel.__mfield_channel_type(this) === 'channel') {
                // disabled on `channel` channels for performance reasons
                return;
            }
            this.env.models['mail.thread_partner_seen_info'].insert({
                __mfield_channelId: channel.__mfield_id(this),
                __mfield_lastFetchedMessage: [['insert', {
                    __mfield_id: last_message_id,
                }]],
                __mfield_partnerId: partner_id,
            });
            channel.update({
                __mfield_messageSeenIndicators: [['insert',
                    {
                        __mfield_channelId: channel.__mfield_id(this),
                        __mfield_messageId: last_message_id,
                    }
                ]],
            });
            // FIXME force the computing of message values (cf task-2261221)
            this.env.models['mail.message_seen_indicator'].recomputeFetchedValues(channel);
        }

        /**
         * @private
         * @param {integer} channelId
         * @param {Object} messageData
         */
        async _handleNotificationChannelMessage(channelId, messageData) {
            let channel = this.env.models['mail.thread'].findFromIdentifyingData({
                __mfield_id: channelId,
                __mfield_model: 'mail.channel',
            });
            const wasChannelExisting = !!channel;
            const convertedData = this.env.models['mail.message'].convertData(messageData);
            const oldMessage = this.env.models['mail.message'].findFromIdentifyingData(convertedData);
            // locally save old values, as insert would overwrite them
            const oldMessageModerationStatus = (
                oldMessage && oldMessage.__mfield_moderation_status(this)
            );
            const oldMessageWasModeratedByCurrentPartner = (
                oldMessage && oldMessage.__mfield_isModeratedByCurrentPartner(this)
            );

            // Fetch missing info from channel before going further. Inserting
            // a channel with incomplete info can lead to issues. This is in
            // particular the case with the `uuid` field that is assumed
            // "required" by the rest of the code and is necessary for some
            // features such as chat windows.
            if (!channel) {
                channel = (await this.async(() =>
                    this.env.models['mail.thread'].performRpcChannelInfo({ ids: [channelId] })
                ))[0];
            }
            if (!channel.__mfield_isPinned(this)) {
                channel.update({
                    __mfield_isPendingPinned: true,
                });
            }

            const message = this.env.models['mail.message'].insert(convertedData);

            // If the message was already known: nothing else should be done,
            // except if it was pending moderation by the current partner, then
            // decrement the moderation counter.
            if (oldMessage) {
                if (
                    oldMessageModerationStatus === 'pending_moderation' &&
                    message.__mfield_moderation_status(this) !== 'pending_moderation' &&
                    oldMessageWasModeratedByCurrentPartner
                ) {
                    const moderation = this.env.messaging.__mfield_moderation(this);
                    moderation.update({
                        __mfield_counter: moderation.__mfield_counter(this) - 1,
                    });
                }
                return;
            }

            // If the current partner is author, do nothing else.
            if (message.__mfield_author(this) === this.env.messaging.__mfield_currentPartner(this)) {
                return;
            }

            // Message from mailing channel should not make a notification in
            // Odoo for users with notification "Handled by Email".
            // Channel has been marked as read server-side in this case, so
            // it should not display a notification by incrementing the
            // unread counter.
            if (
                channel.__mfield_mass_mailing(this) &&
                this.env.session.notification_type === 'email'
            ) {
                return;
            }
            // In all other cases: update counter and notify if necessary

            // Chat from OdooBot is considered disturbing and should only be
            // shown on the menu, but no notification and no thread open.
            const isChatWithOdooBot = (
                channel.__mfield_correspondent(this) &&
                channel.__mfield_correspondent(this) === this.env.messaging.__mfield_partnerRoot(this)
            );
            if (!isChatWithOdooBot) {
                // Notify if out of focus
                const isOdooFocused = this.env.services['bus_service'].isOdooFocused();
                if (!isOdooFocused) {
                    this._notifyNewChannelMessageWhileOutOfFocus({
                        channel,
                        message,
                    });
                }
                if (
                    channel.__mfield_model(this) === 'mail.channel' &&
                    channel.__mfield_channel_type(this) !== 'channel'
                ) {
                    // disabled on non-channel threads and
                    // on `channel` channels for performance reasons
                    channel.markAsFetched();
                }
                // (re)open chat on receiving new message
                if (channel.__mfield_channel_type(this) !== 'channel') {
                    this.env.messaging.__mfield_chatWindowManager(this).openThread(channel);
                }
            }

            // If the channel wasn't known its correct counter was fetched at
            // the start of the method, no need update it here.
            if (!wasChannelExisting) {
                return;
            }
            // manually force recompute of counter
            this.__mfield_messaging(this).__mfield_messagingMenu(this).update();
        }

        /**
         * Called when a channel has been seen, and the server responds with the
         * last message seen. Useful in order to track last message seen.
         *
         * @private
         * @param {integer} channelId
         * @param {Object} param1
         * @param {integer} param1.last_message_id
         * @param {integer} param1.partner_id
         */
        async _handleNotificationChannelSeen(channelId, {
            last_message_id,
            partner_id,
        }) {
            const channel = this.env.models['mail.thread'].findFromIdentifyingData({
                __mfield_id: channelId,
                __mfield_model: 'mail.channel',
            });
            if (!channel) {
                // for example seen from another browser, the current one has no
                // knowledge of the channel
                return;
            }
            const lastMessage = this.env.models['mail.message'].insert({
                __mfield_id: last_message_id,
            });
            // restrict computation of seen indicator for "non-channel" channels
            // for performance reasons
            const shouldComputeSeenIndicators = channel.__mfield_channel_type(this) !== 'channel';
            const updateData = {};
            if (shouldComputeSeenIndicators) {
                this.env.models['mail.thread_partner_seen_info'].insert({
                    __mfield_channelId: channel.__mfield_id(this),
                    __mfield_lastSeenMessage: [['link', lastMessage]],
                    __mfield_partnerId: partner_id,
                });
                Object.assign(updateData, {
                    // FIXME should no longer use computeId (task-2335647)
                    __mfield_messageSeenIndicators: [['insert',
                        {
                            __mfield_channelId: channel.__mfield_id(this),
                            __mfield_messageId: lastMessage.__mfield_id(this),
                        },
                    ]],
                });
            }
            if (this.env.messaging.__mfield_currentPartner(this).__mfield_id(this) === partner_id) {
                Object.assign(updateData, {
                    __mfield_lastSeenByCurrentPartnerMessageId: last_message_id,
                    __mfield_pendingSeenMessageId: undefined,
                });
            }
            channel.update(updateData);
            if (shouldComputeSeenIndicators) {
                // FIXME force the computing of thread values (cf task-2261221)
                this.env.models['mail.thread'].computeLastCurrentPartnerMessageSeenByEveryone(channel);
                // FIXME force the computing of message values (cf task-2261221)
                this.env.models['mail.message_seen_indicator'].recomputeSeenValues(channel);
            }
            // manually force recompute of counter
            this.__mfield_messaging(this).__mfield_messagingMenu(this).update();
        }

        /**
         * @private
         * @param {integer} channelId
         * @param {Object} param1
         * @param {boolean} param1.is_typing
         * @param {integer} param1.partner_id
         */
        _handleNotificationChannelTypingStatus(channelId, { is_typing, partner_id }) {
            const channel = this.env.models['mail.thread'].findFromIdentifyingData({
                __mfield_id: channelId,
                __mfield_model: 'mail.channel',
            });
            if (!channel) {
                return;
            }
            const partner = this.env.models['mail.partner'].insert({
                __mfield_id: partner_id,
            });
            if (partner === this.env.messaging.__mfield_currentPartner(this)) {
                // Ignore management of current partner is typing notification.
                return;
            }
            if (is_typing) {
                if (channel.__mfield_typingMembers(this).includes(partner)) {
                    channel.refreshOtherMemberTypingMember(partner);
                } else {
                    channel.registerOtherMemberTypingMember(partner);
                }
            } else {
                if (!channel.__mfield_typingMembers(this).includes(partner)) {
                    // Ignore no longer typing notifications of members that
                    // are not registered as typing something.
                    return;
                }
                channel.unregisterOtherMemberTypingMember(partner);
            }
        }

        /**
         * @private
         * @param {Object} data
         */
        _handleNotificationNeedaction(data) {
            const message = this.env.models['mail.message'].insert(
                this.env.models['mail.message'].convertData(data)
            );
            const inboxMailbox = this.env.messaging.__mfield_inbox(this);
            inboxMailbox.update({
                __mfield_counter: inboxMailbox.__mfield_counter(this) + 1,
            });
            for (const thread of message.__mfield_threads(this)) {
                if (
                    thread.__mfield_channel_type(this) === 'channel' &&
                    message.__mfield_isNeedaction(this)
                ) {
                    thread.update({
                        __mfield_message_needaction_counter: thread.__mfield_message_needaction_counter(this) + 1,
                    });
                }
            }
            // manually force recompute of counter
            this.__mfield_messaging(this).__mfield_messagingMenu(this).update();
        }

        /**
         * @private
         * @param {Object} data
         * @param {string} [data.info]
         * @param {string} [data.type]
         */
        async _handleNotificationPartner(data) {
            const {
                info,
                type,
            } = data;
            if (type === 'activity_updated') {
                this.env.bus.trigger('activity_updated', data);
            } else if (type === 'author') {
                return this._handleNotificationPartnerAuthor(data);
            } else if (info === 'channel_seen') {
                return this._handleNotificationChannelSeen(data.channel_id, {
                    last_message_id: data.last_message_id,
                    partner_id: this.env.messaging.__mfield_currentPartner(this).__mfield_id(this),
                });
            } else if (type === 'deletion') {
                return this._handleNotificationPartnerDeletion(data);
            } else if (type === 'message_notification_update') {
                return this._handleNotificationPartnerMessageNotificationUpdate(data.elements);
            } else if (type === 'mark_as_read') {
                return this._handleNotificationPartnerMarkAsRead(data);
            } else if (type === 'moderator') {
                return this._handleNotificationPartnerModerator(data);
            } else if (type === 'simple_notification') {
                const escapedTitle = owl.utils.escape(data.title);
                const escapedMessage = owl.utils.escape(data.message);
                this.env.services['notification'].notify({
                    message: escapedMessage,
                    sticky: data.sticky,
                    title: escapedTitle,
                    type: data.warning ? 'warning' : 'danger',
                });
            } else if (type === 'toggle_star') {
                return this._handleNotificationPartnerToggleStar(data);
            } else if (info === 'transient_message') {
                return this._handleNotificationPartnerTransientMessage(data);
            } else if (info === 'unsubscribe') {
                return this._handleNotificationPartnerUnsubscribe(data.id);
            } else if (type === 'user_connection') {
                return this._handleNotificationPartnerUserConnection(data);
            } else {
                return this._handleNotificationPartnerChannel(data);
            }
        }

        /**
         * @private
         * @param {Object} data
         * @param {Object} data.message
         */
        _handleNotificationPartnerAuthor(data) {
            this.env.models['mail.message'].insert(
                this.env.models['mail.message'].convertData(data.message)
            );
        }

        /**
         * @private
         * @param {Object} data
         * @param {string} data.channel_type
         * @param {integer} data.id
         * @param {string} [data.info]
         * @param {boolean} data.is_minimized
         * @param {string} data.name
         * @param {string} data.state
         * @param {string} data.uuid
         */
        _handleNotificationPartnerChannel(data) {
            const convertedData = this.env.models['mail.thread'].convertData(
                Object.assign({
                    __mfield_model: 'mail.channel',
                }, data)
            );

            let channel = this.env.models['mail.thread'].findFromIdentifyingData(convertedData);
            const wasCurrentPartnerMember = (
                channel &&
                channel.__mfield_members(this).includes(this.env.messaging.__mfield_currentPartner(this))
            );

            channel = this.env.models['mail.thread'].insert(convertedData);
            if (
                channel.__mfield_channel_type(this) === 'channel' &&
                data.info !== 'creation' &&
                !wasCurrentPartnerMember
            ) {
                this.env.services['notification'].notify({
                    message: _.str.sprintf(
                        this.env._t("You have been invited to: %s"),
                        owl.utils.escape(channel.__mfield_name(this))
                    ),
                    title: this.env._t("Invitation"),
                    type: 'warning',
                });
            }
            // a new thread with unread messages could have been added
            // manually force recompute of counter
            this.__mfield_messaging(this).__mfield_messagingMenu(this).update();
        }

        /**
         * @private
         * @param {Object} param0
         * @param {integer[]} param0.messag_ids
         */
        _handleNotificationPartnerDeletion({ message_ids }) {
            const moderationMailbox = this.env.messaging.__mfield_moderation(this);
            for (const id of message_ids) {
                const message = this.env.models['mail.message'].find(message => message.__mfield_id(this) === id);
                if (message) {
                    if (
                        message.__mfield_moderation_status(this) === 'pending_moderation' &&
                        message.__mfield_originThread(this).__mfield_isModeratedByCurrentPartner(this)
                    ) {
                        moderationMailbox.update({
                            __mfield_counter: moderationMailbox.__mfield_counter(this) - 1,
                        });
                    }
                    message.delete();
                }
            }
            // deleting message might have deleted notifications, force recompute
            this.__mfield_messaging(this).__mfield_notificationGroupManager(this).computeGroups();
            // manually force recompute of counter (after computing the groups)
            this.__mfield_messaging(this).__mfield_messagingMenu(this).update();
        }

        /**
         * @private
         * @param {Object} data
         */
        _handleNotificationPartnerMessageNotificationUpdate(data) {
            for (const messageData of data) {
                const message = this.env.models['mail.message'].insert(
                    this.env.models['mail.message'].convertData(messageData)
                );
                // implicit: failures are sent by the server as notification
                // only if the current partner is author of the message
                if (
                    !message.__mfield_author(this) &&
                    this.__mfield_messaging(this).__mfield_currentPartner(this)
                ) {
                    message.update({
                        __mfield_author: [['link', this.__mfield_messaging(this).__mfield_currentPartner(this)]],
                    });
                }
            }
            this.__mfield_messaging(this).__mfield_notificationGroupManager(this).computeGroups();
            // manually force recompute of counter (after computing the groups)
            this.__mfield_messaging(this).__mfield_messagingMenu(this).update();
        }

        /**
         * @private
         * @param {Object} param0
         * @param {integer[]} [param0.channel_ids
         * @param {integer[]} [param0.message_ids=[]]
         */
        _handleNotificationPartnerMarkAsRead({ channel_ids, message_ids = [] }) {
            const inboxMailbox = this.env.messaging.__mfield_inbox(this);

            // 1. move messages from inbox to history
            // AKU TODO: flag other caches to invalidate
            // task-2171873
            for (const message_id of message_ids) {
                // We need to ignore all not yet known messages because we don't want them
                // to be shown partially as they would be linked directly to mainCache
                // Furthermore, server should not send back all message_ids marked as read
                // but something like last read message_id or something like that.
                // (just imagine you mark 1000 messages as read ... )
                const message = this.env.models['mail.message'].find(m => m.__mfield_id(this) === message_id);
                if (message) {
                    message.update({
                        __mfield_isNeedaction: false,
                        __mfield_isHistory: true,
                    });
                }
            }

            // 2. remove "needaction" from channels
            let channels;
            if (channel_ids) {
                channels = channel_ids
                    .map(id => this.env.models['mail.thread'].find(thread =>
                        thread.__mfield_id(this) === id &&
                        thread.__mfield_model(this) === 'mail.channel'
                    ))
                    .filter(thread => !!thread);
            } else {
                // flux specific: channel_ids unset means "mark all as read"
                channels = this.env.models['mail.thread'].all(thread =>
                    thread.__mfield_model(this) === 'mail.channel'
                );
            }
            for (const channel of channels) {
                channel.update({
                    __mfield_message_needaction_counter: 0,
                });
            }
            inboxMailbox.update({
                __mfield_counter: inboxMailbox.__mfield_counter(this) - message_ids.length,
            });

            // manually force recompute of counter
            this.__mfield_messaging(this).__mfield_messagingMenu(this).update();
        }

        /**
         * @private
         * @param {Object} param0
         * @param {Object} param0.message
         */
        _handleNotificationPartnerModerator({ message: data }) {
            this.env.models['mail.message'].insert(
                this.env.models['mail.message'].convertData(data)
            );
            const moderationMailbox = this.env.messaging.__mfield_moderation(this);
            if (moderationMailbox) {
                moderationMailbox.update({
                    __mfield_counter: moderationMailbox.__mfield_counter(this) + 1,
                });
            }
            // manually force recompute of counter
            this.__mfield_messaging(this).__mfield_messagingMenu(this).update();
        }

        /**
         * @private
         * @param {Object} param0
         * @param {integer[]} param0.message_ids
         * @param {boolean} param0.starred
         */
        _handleNotificationPartnerToggleStar({ message_ids = [], starred }) {
            const starredMailbox = this.env.messaging.__mfield_starred(this);
            for (const messageId of message_ids) {
                const message = this.env.models['mail.message'].find(message =>
                    message.__mfield_id(this) === messageId
                );
                if (!message) {
                    continue;
                }
                message.update({
                    __mfield_isStarred: starred,
                });
                if (!starred) {
                    // AKU TODO: flag starred other caches for invalidation
                    // task-2171873
                }
                starredMailbox.update({
                    __mfield_counter: starred
                        ? starredMailbox.__mfield_counter(this) + 1
                        : starredMailbox.__mfield_counter(this) -1,
                });
            }
        }

        /**
         * On receiving a transient message, i.e. a message which does not come
         * from a member of the channel. Usually a log message, such as one
         * generated from a command with ('/').
         *
         * @private
         * @param {Object} data
         */
        _handleNotificationPartnerTransientMessage(data) {
            const convertedData = this.env.models['mail.message'].convertData(data);
            const messageIds = this.env.models['mail.message'].all().map(message => message.__mfield_id(this));
            const partnerRoot = this.env.messaging.__mfield_partnerRoot(this);
            this.env.models['mail.message'].create(Object.assign(convertedData, {
                __mfield_author: [['link', partnerRoot]],
                __mfield_id: (messageIds ? Math.max(...messageIds) : 0) + 0.01,
                __mfield_isTransient: true,
            }));
        }

        /**
         * @private
         * @param {integer} channelId
         */
        _handleNotificationPartnerUnsubscribe(channelId) {
            const channel = this.env.models['mail.thread'].find(thread =>
                thread.__mfield_id(this) === channelId &&
                thread.__mfield_model(this) === 'mail.channel'
            );
            if (!channel) {
                return;
            }
            let message;
            if (channel.__mfield_correspondent(this)) {
                const correspondent = channel.__mfield_correspondent(this);
                message = _.str.sprintf(
                    this.env._t("You unpinned your conversation with <b>%s</b>."),
                    owl.utils.escape(correspondent.__mfield_name(this))
                );
            } else {
                message = _.str.sprintf(
                    this.env._t("You unsubscribed from <b>%s</b>."),
                    owl.utils.escape(channel.__mfield_name(this))
                );
            }
            // We assume that arriving here the server has effectively
            // unpinned the channel
            channel.update({
                __mfield_isServerPinned: false,
            });
            this.env.services['notification'].notify({
                message,
                title: this.env._t("Unsubscribed"),
                type: 'warning',
            });
        }

        /**
         * @private
         * @param {Object} param0
         * @param {string} param0.message
         * @param {integer} param0.partner_id
         * @param {string} param0.title
         */
        async _handleNotificationPartnerUserConnection({ message, partner_id, title }) {
            // If the current user invited a new user, and the new user is
            // connecting for the first time while the current user is present
            // then open a chat for the current user with the new user.
            this.env.services['bus_service'].sendNotification(title, message);
            const chat = await this.async(() =>
                this.env.messaging.getChat({ partnerId: partner_id }
            ));
            if (!chat) {
                return;
            }
            this.env.messaging.__mfield_chatWindowManager(this).openThread(chat);
        }

        /**
         * @private
         * @param {Object} param0
         * @param {mail.thread} param0.channel
         * @param {mail.message} param0.message
         */
        _notifyNewChannelMessageWhileOutOfFocus({ channel, message }) {
            const author = message.__mfield_author(this);
            const messaging = this.env.messaging;
            let notificationTitle;
            if (!author) {
                notificationTitle = this.env._t("New message");
            } else {
                const authorName = author.__mfield_nameOrDisplayName(this);
                if (channel.__mfield_channel_type(this) === 'channel') {
                    // hack: notification template does not support OWL components,
                    // so we simply use their template to make HTML as if it comes
                    // from component
                    const channelIcon = this.env.qweb.renderToString('mail.ThreadIcon', {
                        env: this.env,
                        thread: channel,
                    });
                    const channelName = owl.utils.escape(channel.__mfield_displayName(this));
                    const channelNameWithIcon = channelIcon + channelName;
                    notificationTitle = _.str.sprintf(
                        this.env._t("%s from %s"),
                        owl.utils.escape(authorName),
                        channelNameWithIcon
                    );
                } else {
                    notificationTitle = owl.utils.escape(authorName);
                }
            }
            const notificationContent = message.__mfield_prettyBody(this).substr(0, PREVIEW_MSG_MAX_SIZE);
            this.env.services['bus_service'].sendNotification(notificationTitle, notificationContent);
            messaging.update({
                __mfield_outOfFocusUnreadMessageCounter: messaging.__mfield_outOfFocusUnreadMessageCounter(this) + 1,
            });
            const titlePattern = messaging.__mfield_outOfFocusUnreadMessageCounter(this) === 1
                ? this.env._t("%d Message")
                : this.env._t("%d Messages");
            this.env.bus.trigger('set_title_part', {
                part: '_chat',
                title: _.str.sprintf(titlePattern, messaging.__mfield_outOfFocusUnreadMessageCounter(this)),
            });
        }

    }

    MessagingNotificationHandler.fields = {
        __mfield_messaging: one2one('mail.messaging', {
            inverse: '__mfield_notificationHandler',
        }),
    };

    MessagingNotificationHandler.modelName = 'mail.messaging_notification_handler';

    return MessagingNotificationHandler;
}

registerNewModel('mail.messaging_notification_handler', factory);

});
