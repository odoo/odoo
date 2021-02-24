odoo.define('mail/static/src/models/messaging_notification_handler/messaging_notification_handler.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { one2one } = require('mail/static/src/model/model_field.js');
const { decrement, increment, insert, link } = require('mail/static/src/model/model_field_command.js');
const { htmlToTextContentInline } = require('mail.utils');

const PREVIEW_MSG_MAX_SIZE = 350; // optimal for native English speakers

function factory(dependencies) {

    class MessagingNotificationHandler extends dependencies['mail.model'] {

        /**
         * @override
         */
        _willDelete() {
            // TODO SEB cleanup
            if (this.env.services['bus_service']) {
                this.env.services['bus_service'].off('notification');
                this.env.services['bus_service'].stopPolling();
            }
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
            const {
                services: {
                    'bus.server_communication': serverCommunication,
                },
            } = this.env;
            // TODO SEB move this into auth_signup override
            serverCommunication.on('mail.auth_signup', payload => this._handleNotificationFirstUserConnection(payload));
            serverCommunication.on('mail.channel_create', payload => this._handleNotificationChannelCreate(payload));
            serverCommunication.on('mail.channel_fetched', payload => this._handleNotificationChannelFetched(payload));
            serverCommunication.on('mail.channel_fold_state_changed', payload => this._handleNotificationChannelFoldStateChanged(payload));
            serverCommunication.on('mail.channel_info', payload => this._handleNotificationChannelInfo(payload));
            serverCommunication.on('mail.channel_is_pinned_changed', payload => this._handleNotificationChannelIsPinnedChanged(payload));
            serverCommunication.on('mail.channel_join', payload => this._handleNotificationChannelJoin(payload));
            serverCommunication.on('mail.channel_new_message', payload => this._handleNotificationChannelNewMessage(payload));
            serverCommunication.on('mail.channel_seen', payload => this._handleNotificationChannelSeen(payload));
            serverCommunication.on('mail.channel_typing_status', payload => this._handleNotificationChannelTypingStatus(payload));
            serverCommunication.on('mail.channel_unsubscribe', payload => this._handleNotificationChannelUnsubscribe(payload));
            serverCommunication.on('mail.inbox_mark_all_messages_as_read', payload => this._handleNotificationInboxMarkAllMessagesAsRead(payload));
            serverCommunication.on('mail.inbox_mark_messages_as_read', payload => this._handleNotificationInboxMarkMessagesAsRead(payload));
            serverCommunication.on('mail.inbox_new_message', payload => this._handleNotificationInboxNewMessage(payload));
            serverCommunication.on('mail.message_deleted', payload => this._handleNotificationMessageDeletion(payload));
            serverCommunication.on('mail.message_notification_update', payload => this._handleNotificationMessageNotificationUpdate(payload));
            serverCommunication.on('mail.message_pending_moderation', payload => this._handleNotificationMessagePendingModeration(payload));
            serverCommunication.on('mail.message_toggle_star', payload => this._handleNotificationMessageToggleStar(payload));
            serverCommunication.on('mail.simple_notification', payload => this._handleNotificationSimpleNotification(payload));
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @param {Object[]} notifications
         * @param {any} [notifications[].payload]
         * @param {string} notifications[].type
         */
        async _handleNotifications(notifications) {
            // TODO SEB restore/handle corretly the unsubscribe stuff

            // const proms = notifications.map(notification => {
            //     const [channel, message] = notification;
            //     const [, model, id] = channel;
            //     switch (model) {
            //         case 'res.partner':
            //             if (id !== this.env.messaging.currentPartner.id) {
            //                 // ignore broadcast to other partners
            //                 return;
            //             }
            //             return this._handleNotificationPartner(Object.assign({}, message));
            //         default:
            //             console.warn(`mail.messaging_notification_handler: Unhandled notification "${model}"`);
            //             return;
            //     }
            // });
            // await this.async(() => Promise.all(proms));
        }

        /**
         * @private
         * @param {Object} payload
         * @param {integer} payload.id
         * @param {integer} payload.last_message_id
         * @param {integer} payload.partner_id
         */
        async _handleNotificationChannelFetched({ id, last_message_id, partner_id }) {
            const channel = this.env.models['mail.thread'].findFromIdentifyingData({
                id: id,
                model: 'mail.channel',
            });
            if (!channel) {
                // for example seen from another browser, the current one has no
                // knowledge of the channel
                return;
            }
            if (channel.channel_type === 'channel') {
                // disabled on `channel` channels for performance reasons
                return;
            }
            this.env.models['mail.thread_partner_seen_info'].insert({
                channelId: channel.id,
                lastFetchedMessage: insert({ id: last_message_id }),
                partnerId: partner_id,
            });
            this.env.models['mail.message_seen_indicator'].insert({
                channelId: channel.id,
                messageId: last_message_id,
            });
            // FIXME force the computing of message values (cf task-2261221)
            this.env.models['mail.message_seen_indicator'].recomputeFetchedValues(channel);
        }

        /**
         * @private
         * @param {Object} payload
         * @param {integer} payload.channel_id
         * @param {Object} payload.message
         */
        async _handleNotificationChannelNewMessage({ channel_id, message: messageData }) {
            let channel = this.env.models['mail.thread'].findFromIdentifyingData({
                id: channel_id,
                model: 'mail.channel',
            });
            const wasChannelExisting = !!channel;
            const convertedData = this.env.models['mail.message'].convertData(messageData);
            const oldMessage = this.env.models['mail.message'].findFromIdentifyingData(convertedData);
            // locally save old values, as insert would overwrite them
            const oldMessageModerationStatus = (
                oldMessage && oldMessage.moderation_status
            );
            const oldMessageWasModeratedByCurrentPartner = (
                oldMessage && oldMessage.isModeratedByCurrentPartner
            );

            // Fetch missing info from channel before going further. Inserting
            // a channel with incomplete info can lead to issues. This is in
            // particular the case with the `uuid` field that is assumed
            // "required" by the rest of the code and is necessary for some
            // features such as chat windows.
            if (!channel) {
                channel = (await this.async(() =>
                    this.env.models['mail.thread'].performRpcChannelInfo({ ids: [channel_id] })
                ))[0];
            }
            if (!channel.isPinned) {
                channel.pin();
            }

            const message = this.env.models['mail.message'].insert(convertedData);
            this._notifyThreadViewsMessageReceived(message);

            // If the message was already known: nothing else should be done,
            // except if it was pending moderation by the current partner, then
            // decrement the moderation counter.
            if (oldMessage) {
                if (
                    oldMessageModerationStatus === 'pending_moderation' &&
                    message.moderation_status !== 'pending_moderation' &&
                    oldMessageWasModeratedByCurrentPartner
                ) {
                    const moderation = this.env.messaging.moderation;
                    moderation.update({ counter: decrement() });
                }
                return;
            }

            // If the current partner is author, do nothing else.
            if (message.author === this.env.messaging.currentPartner) {
                return;
            }

            // Message from mailing channel should not make a notification in
            // Odoo for users with notification "Handled by Email".
            // Channel has been marked as read server-side in this case, so
            // it should not display a notification by incrementing the
            // unread counter.
            if (
                channel.mass_mailing &&
                this.env.session.notification_type === 'email'
            ) {
                return;
            }
            // In all other cases: update counter and notify if necessary

            // Chat from OdooBot is considered disturbing and should only be
            // shown on the menu, but no notification and no thread open.
            const isChatWithOdooBot = (
                channel.correspondent &&
                channel.correspondent === this.env.messaging.partnerRoot
            );
            if (!isChatWithOdooBot) {
                // const isOdooFocused = this.env.services['bus_service'].isOdooFocused();
                // Notify if out of focus
                // if (!isOdooFocused && channel.isChatChannel) {
                //     this._notifyNewChannelMessageWhileOutOfFocus({
                //         channel,
                //         message,
                //     });
                // }
                if (channel.model === 'mail.channel' && channel.channel_type !== 'channel') {
                    // disabled on non-channel threads and
                    // on `channel` channels for performance reasons
                    channel.markAsFetched();
                }
                // (re)open chat on receiving new message
                if (channel.channel_type !== 'channel' && !this.env.messaging.device.isMobile) {
                    this.env.messaging.chatWindowManager.openThread(channel);
                }
            }

            // If the channel wasn't known its correct counter was fetched at
            // the start of the method, no need update it here.
            if (!wasChannelExisting) {
                return;
            }
            // manually force recompute of counter
            this.messaging.messagingMenu.update();
        }

        /**
         * Called when a channel has been seen, and the server responds with the
         * last message seen. Useful in order to track last message seen.
         *
         * @private
         * @param {Object} payload
         * @param {integer} payload.channel_id
         * @param {integer} payload.last_message_id
         * @param {integer} payload.partner_id
         */
        async _handleNotificationChannelSeen({ channel_id, last_message_id, partner_id, }) {
            const channel = this.env.models['mail.thread'].findFromIdentifyingData({
                id: channel_id,
                model: 'mail.channel',
            });
            if (!channel) {
                // for example seen from another browser, the current one has no
                // knowledge of the channel
                return;
            }
            const lastMessage = this.env.models['mail.message'].insert({ id: last_message_id });
            // restrict computation of seen indicator for "non-channel" channels
            // for performance reasons
            const shouldComputeSeenIndicators = channel.channel_type !== 'channel';
            if (shouldComputeSeenIndicators) {
                this.env.models['mail.thread_partner_seen_info'].insert({
                    channelId: channel.id,
                    lastSeenMessage: link(lastMessage),
                    partnerId: partner_id,
                });
                this.env.models['mail.message_seen_indicator'].insert({
                    channelId: channel.id,
                    messageId: lastMessage.id,
                });
            }
            if (this.env.messaging.currentPartner.id === partner_id) {
                channel.update({
                    lastSeenByCurrentPartnerMessageId: last_message_id,
                    pendingSeenMessageId: undefined,
                });
            }
            if (shouldComputeSeenIndicators) {
                // FIXME force the computing of thread values (cf task-2261221)
                this.env.models['mail.thread'].computeLastCurrentPartnerMessageSeenByEveryone(channel);
                // FIXME force the computing of message values (cf task-2261221)
                this.env.models['mail.message_seen_indicator'].recomputeSeenValues(channel);
            }
            // manually force recompute of counter
            this.messaging.messagingMenu.update();
        }

        /**
         * @private
         * @param {Object} payload
         * @param {integer} payload.channel_id
         * @param {boolean} payload.is_typing
         * @param {integer} payload.partner_id
         * @param {string} payload.partner_name
         */
        _handleNotificationChannelTypingStatus({ channel_id, is_typing, partner_id, partner_name }) {
            const channel = this.env.models['mail.thread'].findFromIdentifyingData({
                id: channel_id,
                model: 'mail.channel',
            });
            if (!channel) {
                return;
            }
            const partner = this.env.models['mail.partner'].insert({
                id: partner_id,
                name: partner_name,
            });
            if (partner === this.env.messaging.currentPartner) {
                // Ignore management of current partner is typing notification.
                return;
            }
            if (is_typing) {
                if (channel.typingMembers.includes(partner)) {
                    channel.refreshOtherMemberTypingMember(partner);
                } else {
                    channel.registerOtherMemberTypingMember(partner);
                }
            } else {
                if (!channel.typingMembers.includes(partner)) {
                    // Ignore no longer typing notifications of members that
                    // are not registered as typing something.
                    return;
                }
                channel.unregisterOtherMemberTypingMember(partner);
            }
        }

        /**
         * @private
         * @param {Object} payload
         * @param {Object} payload.message
         */
        _handleNotificationInboxNewMessage({ message: messageData }) {
            const message = this.env.models['mail.message'].insert(
                this.env.models['mail.message'].convertData(messageData)
            );
            this.env.messaging.inbox.update({ counter: increment() });
            const originThread = message.originThread;
            if (originThread) {
                originThread.update({ message_needaction_counter: increment() });
            }
            // manually force recompute of counter
            this.messaging.messagingMenu.update();
        }

        // TODO SEB remake or convert those
        // /**
        //  * @private
        //  * @param {Object} data
        //  * @param {string} [data.info]
        //  * @param {string} [data.type]
        //  */
        // async _handleNotificationPartner(data) {
        //     const {
        //         info,
        //         type,
        //     } = data;
        //     if (type === 'activity_updated') {
        //         this.env.bus.trigger('activity_updated', data);
        //     } else if (info === 'transient_message') {
        //         return this._handleNotificationPartnerTransientMessage(data);
        //     } else if (!type) {
        //         return this._handleNotificationPartnerChannel(data);
        //     }
        // }

        /**
         * @private
         * @param {Object} payload
         * @param {Object} payload.message
         */
        _handleNotificationMessagePendingModeration({ message: messageData }) {
            const message = this.env.models['mail.message'].insert(
                this.env.models['mail.message'].convertData(messageData)
            );
            if (message.originThread.isModeratedByCurrentPartner) {
                this.env.messaging.moderation.update({ counter: increment() });
            }
            // manually force recompute of counter
            this.messaging.messagingMenu.update();
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
                Object.assign({ model: 'mail.channel' }, data)
            );
            if (!convertedData.members) {
                // channel_info does not return all members of channel for
                // performance reasons, but code is expecting to know at
                // least if the current partner is member of it.
                // (e.g. to know when to display "invited" notification)
                // Current partner can always be assumed to be a member of
                // channels received through this notification.
                convertedData.members = link(this.env.messaging.currentPartner);
            }
            let channel = this.env.models['mail.thread'].findFromIdentifyingData(convertedData);
            const wasCurrentPartnerMember = (
                channel &&
                channel.members.includes(this.env.messaging.currentPartner)
            );

            channel = this.env.models['mail.thread'].insert(convertedData);
            if (
                channel.channel_type === 'channel' &&
                data.info !== 'creation' &&
                !wasCurrentPartnerMember
            ) {
                this.env.services['notification'].notify({
                    message: _.str.sprintf(
                        this.env._t("You have been invited to: %s"),
                        owl.utils.escape(channel.name)
                    ),
                    type: 'info',
                });
            }
            // a new thread with unread messages could have been added
            // manually force recompute of counter
            this.messaging.messagingMenu.update();
        }

        /**
         * @private
         * @param {Object} payload
         * @param {integer[]} payload.message_ids
         */
        _handleNotificationMessageDeletion({ message_ids }) {
            const moderationMailbox = this.env.messaging.moderation;
            for (const id of message_ids) {
                const message = this.env.models['mail.message'].findFromIdentifyingData({ id });
                if (!message) {
                    continue;
                }
                if (
                    message.moderation_status === 'pending_moderation' &&
                    message.originThread.isModeratedByCurrentPartner
                ) {
                    moderationMailbox.update({ counter: decrement() });
                }
                message.delete();
            }
            // deleting message might have deleted notifications, force recompute
            this.messaging.notificationGroupManager.computeGroups();
            // manually force recompute of counter (after computing the groups)
            this.messaging.messagingMenu.update();
        }

        /**
         * @private
         * @param {Object[]} messages
         */
        _handleNotificationMessageNotificationUpdate(messages) {
            for (const messageData of messages) {
                const message = this.env.models['mail.message'].insert(
                    this.env.models['mail.message'].convertData(messageData)
                );
                // implicit: failures are sent by the server as notification
                // only if the current partner is author of the message
                if (!message.author && this.messaging.currentPartner) {
                    message.update({ author: link(this.messaging.currentPartner) });
                }
            }
            this.messaging.notificationGroupManager.computeGroups();
            // manually force recompute of counter (after computing the groups)
            this.messaging.messagingMenu.update();
        }

        /**
         * @private
         * @param {Object} payload
         * @param {integer[]} payload.message_ids
         * @param {boolean} payload.starred
         */
        _handleNotificationMessageToggleStar({ message_ids, starred }) {
            for (const messageId of message_ids) {
                const message = this.env.models['mail.message'].findFromIdentifyingData({
                    id: messageId,
                });
                if (!message) {
                    continue;
                }
                message.update({ isStarred: starred });
                this.env.messaging.starred.update({
                    counter: starred ? increment() : decrement(),
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
            const lastMessageId = this.env.models['mail.message'].all().reduce(
                (lastMessageId, message) => Math.max(lastMessageId, message.id),
                0
            );
            const partnerRoot = this.env.messaging.partnerRoot;
            const message = this.env.models['mail.message'].create(Object.assign(convertedData, {
                author: link(partnerRoot),
                id: lastMessageId + 0.01,
                isTransient: true,
            }));
            this._notifyThreadViewsMessageReceived(message);
            // manually force recompute of counter
            this.messaging.messagingMenu.update();
        }

        /**
         * @private
         * @param {Object} payload
         * @param {Object} payload.channel
         */
        _handleNotificationChannelFoldStateChanged({ channel: channelData }) {
            this.env.models['mail.thread'].insert(
                this.env.models['mail.thread'].convertData(Object.assign({ model: 'mail.channel' }, channelData))
            );
        }

        /**
         * @private
         * @param {Object} payload
         * @param {Object} payload.channel
         */
        _handleNotificationChannelInfo({ channel: channelData }) {
            this.env.models['mail.thread'].insert(
                this.env.models['mail.thread'].convertData(Object.assign({ model: 'mail.channel' }, channelData))
            );
        }

        /**
         * @private
         * @param {Object} payload
         * @param {Object} payload.channel
         */
        _handleNotificationChannelCreate({ channel: channelData }) {
            this.env.models['mail.thread'].insert(
                this.env.models['mail.thread'].convertData(Object.assign({ model: 'mail.channel' }, channelData))
            );
        }


        /**
         * @private
         * @param {Object} payload
         * @param {Object} payload.channel
         */
        _handleNotificationChannelIsPinnedChanged({ channel: channelData }) {
            this.env.models['mail.thread'].insert(
                this.env.models['mail.thread'].convertData(Object.assign({ model: 'mail.channel' }, channelData))
            );
        }

        /**
         * @private
         * @param {Object} payload
         * @param {Object} payload.channel
         */
        _handleNotificationChannelUnsubscribe({ channel: channelData }) {
            const channel = this.env.models['mail.thread'].insert(
                this.env.models['mail.thread'].convertData(Object.assign({ model: 'mail.channel' }, channelData))
            );
            let message;
            if (channel.correspondent) {
                const correspondent = channel.correspondent;
                message = _.str.sprintf(
                    this.env._t("You unpinned your conversation with <b>%s</b>."),
                    owl.utils.escape(correspondent.name)
                );
            } else {
                message = _.str.sprintf(
                    this.env._t("You unsubscribed from <b>%s</b>."),
                    owl.utils.escape(channel.name)
                );
            }
            // We assume that arriving here the server has effectively
            // unpinned the channel
            channel.update({ isServerPinned: false });
            this.env.services['notification'].notify({
                message,
                type: 'info',
            });
        }

        /**
         * @private
         * @param {Object} payload
         * @param {Object} payload.partnerData
         */
        async _handleNotificationFirstUserConnection({ partnerData }) {
            // If the current user invited a new user, and the new user is
            // connecting for the first time while the current user is present
            // then open a chat for the current user with the new user.
            const partner = this.env.models['mail.partner'].insert(
                this.env.models['mail.partner'].convertData(partnerData)
            );
            this.env.services['bus_service'].sendNotification({
                message: this.env._t("This is their first connection. Wish them luck."),
                title: _.sprintf(this.env._t("%s connected"), owl.utils.escape(partner.nameOrDisplayName)),
                type: 'info',
            });
            if (this.env.messaging.device.isMobile) {
                return;
            }
            const chat = await this.async(() => partner.getChat());
            if (!chat) {
                return;
            }
            this.env.messaging.chatWindowManager.openThread(chat);
        }

        /**
         * @private
         */
        _handleNotificationInboxMarkAllMessagesAsRead() {
            const inbox = this.env.messaging.inbox;
            // move messages from Inbox to history
            for (const message of inbox.messages) {
                message.update({
                    isHistory: true,
                    isNeedaction: false,
                });
            }
            // update thread counters
            for (const thread of this.env.models['mail.thread'].all()) {
                thread.update({ message_needaction_counter: 0 });
            }
            inbox.update({ counter: 0 });
            // manually force recompute of counter
            this.messaging.messagingMenu.update();
        }

        /**
         * @private
         * @param {Object} payload
         * @param {integer[]} payload.message_ids
         * @param {integer} payload.needaction_inbox_counter
         */
        _handleNotificationInboxMarkMessagesAsRead({ message_ids, needaction_inbox_counter }) {
            for (const message_id of message_ids) {
                // We need to ignore all not yet known messages because we don't want them
                // to be shown partially as they would be linked directly to mainCache
                // Furthermore, server should not send back all message_ids marked as read
                // but something like last read message_id or something like that.
                // (just imagine you mark 1000 messages as read ... )
                const message = this.env.models['mail.message'].findFromIdentifyingData({ id: message_id });
                if (!message) {
                    continue;
                }
                // update thread counter
                const originThread = message.originThread;
                if (originThread && message.isNeedaction) {
                    originThread.update({ message_needaction_counter: decrement() });
                }
                // move messages from Inbox to history
                message.update({
                    isHistory: true,
                    isNeedaction: false,
                });
            }
            const inbox = this.env.messaging.inbox;
            inbox.update({ counter: needaction_inbox_counter });
            if (inbox.counter > inbox.mainCache.fetchedMessages.length) {
                // Force refresh Inbox because depending on what was marked as
                // read the cache might become empty even though there are more
                // messages on the server.
                inbox.mainCache.update({ hasToLoadMessages: true });
            }
            // manually force recompute of counter
            this.messaging.messagingMenu.update();
        }

        /**
         * @private
         * @param {Object} payload
         * @param {string} payload.message
         * @param {boolean} payload.sticky
         * @param {string} payload.warning
         */
        _handleNotificationSimpleNotification({ message, sticky, warning }) {
            // TODO SEB move this handler into /bus
            // TODO SEB also change API to allow proper params to go through
            const escapedMessage = owl.utils.escape(message);
            // TODO SEB use displayNotification
            this.env.services['notification'].notify({
                message: escapedMessage,
                sticky,
                type: warning ? 'warning' : 'danger',
            });
        }

        /**
         * @private
         * @param {Object} param0
         * @param {mail.thread} param0.channel
         * @param {mail.message} param0.message
         */
        _notifyNewChannelMessageWhileOutOfFocus({ channel, message }) {
            const author = message.author;
            const messaging = this.env.messaging;
            let notificationTitle;
            if (!author) {
                notificationTitle = this.env._t("New message");
            } else {
                const escapedAuthorName = owl.utils.escape(author.nameOrDisplayName);
                if (channel.channel_type === 'channel') {
                    // hack: notification template does not support OWL components,
                    // so we simply use their template to make HTML as if it comes
                    // from component
                    const channelIcon = this.env.qweb.renderToString('mail.ThreadIcon', {
                        env: this.env,
                        thread: channel,
                    });
                    const channelName = owl.utils.escape(channel.displayName);
                    const channelNameWithIcon = channelIcon + channelName;
                    notificationTitle = _.str.sprintf(
                        this.env._t("%s from %s"),
                        escapedAuthorName,
                        channelNameWithIcon
                    );
                } else {
                    notificationTitle = escapedAuthorName;
                }
            }
            const notificationContent = htmlToTextContentInline(message.body).substr(0, PREVIEW_MSG_MAX_SIZE);
            this.env.services['bus_service'].sendNotification({
                message: notificationContent,
                title: notificationTitle,
                type: 'info',
            });
            messaging.update({ outOfFocusUnreadMessageCounter: increment() });
            const titlePattern = messaging.outOfFocusUnreadMessageCounter === 1
                ? this.env._t("%d Message")
                : this.env._t("%d Messages");
            this.env.bus.trigger('set_title_part', {
                part: '_chat',
                title: _.str.sprintf(titlePattern, messaging.outOfFocusUnreadMessageCounter),
            });
        }

        /**
         * Notifies threadViews about the given message being just received.
         * This can allow them adjust their scroll position if applicable.
         *
         * @private
         * @param {mail.message}
         */
        _notifyThreadViewsMessageReceived(message) {
            for (const thread of message.threads) {
                for (const threadView of thread.threadViews) {
                    threadView.addComponentHint('message-received', { message });
                }
            }
        }

    }

    MessagingNotificationHandler.fields = {
        messaging: one2one('mail.messaging', {
            inverse: 'notificationHandler',
        }),
    };

    MessagingNotificationHandler.modelName = 'mail.messaging_notification_handler';

    return MessagingNotificationHandler;
}

registerNewModel('mail.messaging_notification_handler', factory);

});
