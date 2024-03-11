/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { decrement, increment, insert } from '@mail/model/model_field_command';
import { htmlToTextContentInline } from '@mail/js/utils';

import { escape, sprintf } from '@web/core/utils/strings';
import { str_to_datetime } from 'web.time';
import { Markup } from 'web.utils';
import { renderToString } from "@web/core/utils/render";

const PREVIEW_MSG_MAX_SIZE = 350; // optimal for native English speakers

registerModel({
    name: 'MessagingNotificationHandler',
    lifecycleHooks: {
        _willDelete() {
            this.env.services['bus_service'].removeEventListener('notification', this._handleNotifications);
        },
    },
    recordMethods: {
        /**
         * Fetch messaging data initially to populate the store specifically for
         * the current users. This includes pinned channels for instance.
         */
        start() {
            this.env.services['bus_service'].addEventListener('notification', this._handleNotifications);
            this.env.services['bus_service'].start();
        },
        /**
         * @private
         * @param {CustomEvent} ev
         * @param {Object[]} [ev.detail] Notifications coming from the bus.
         * @param {Array|string} ev.detail[i][0] meta-data of the notification.
         * @param {string} ev.detail[i][0][0] name of database this
         *   notification comes from.
         * @param {string} ev.detail[i][0][1] type of notification.
         * @param {integer} ev.detail[i][0][2] usually id of related type
         *   of notification. For instance, with `mail.channel`, this is the id
         *   of the channel.
         * @param {Object} ev.detail[i][1] payload of the notification
         */
        async _handleNotifications({ detail: notifications }) {
            const channelsLeft = new Set(
                notifications
                    .filter(notification => notification.type === 'mail.channel/leave')
                    .map(notification => notification.payload.id)
            );
            const proms = notifications.map(message => {
                if (typeof message === 'object') {
                    switch (message.type) {
                        case 'bus/im_status':
                            return this._handleNotificationBusImStatus(message.payload);
                        case 'ir.attachment/delete':
                            return this._handleNotificationAttachmentDelete(message.payload);
                        case 'mail.channel.member/seen':
                            return this._handleNotificationChannelMemberSeen(message.payload);
                        case 'mail.channel.member/fetched':
                            return this._handleNotificationChannelMemberFetched(message.payload);
                        case 'mail.channel.member/typing_status':
                            return this._handleNotificationChannelMemberTypingStatus(message.payload);
                        case 'mail.channel/new_message':
                            if (channelsLeft.has(message.payload.id)) {
                                /**
                                 * `_handleNotificationChannelMessage` tries to pin the channel,
                                 * which is not desirable if the channel was just left.
                                 * The issue happens because the longpolling request resolves with
                                 * notifications for the channel that was just left (the channels
                                 * to observe are determined when the longpolling starts waiting,
                                 * not when it resolves).
                                 */
                                return;
                            }
                            return this._handleNotificationChannelMessage(message.payload);
                        case 'mail.link.preview/insert':
                            this.messaging.models['LinkPreview'].insert(message.payload);
                            return;
                        case 'mail.link.preview/delete': {
                            const linkPreview = this.messaging.models['LinkPreview'].findFromIdentifyingData(message.payload);
                            if (linkPreview) {
                                linkPreview.delete();
                            }
                            return;
                        }
                        case 'mail.message/delete':
                            return this._handleNotificationMessageDelete(message.payload);
                        case 'mail.message/inbox':
                            return this._handleNotificationNeedaction(message.payload);
                        case 'mail.message/mark_as_read':
                            return this._handleNotificationPartnerMarkAsRead(message.payload);
                        case 'mail.message/notification_update':
                            return this._handleNotificationPartnerMessageNotificationUpdate(message.payload);
                        case 'simple_notification':
                            return this._handleNotificationSimpleNotification(message.payload);
                        case 'mail.message/toggle_star':
                            return this._handleNotificationPartnerToggleStar(message.payload);
                        case 'mail.channel/transient_message':
                            return this._handleNotificationPartnerTransientMessage(message.payload);
                        case 'mail.channel/leave':
                            return this._handleNotificationChannelLeave(message.payload);
                        case 'mail.channel/delete':
                            return this._handleNotificationChannelDelete(message.payload);
                        case 'res.users/connection':
                            return this._handleNotificationPartnerUserConnection(message.payload);
                        case 'mail.activity/updated': {
                            for (const activityMenuView of this.messaging.models['ActivityMenuView'].all()) {
                                if (message.payload.activity_created) {
                                    activityMenuView.update({ extraCount: increment() });
                                }
                                if (message.payload.activity_deleted) {
                                    activityMenuView.update({ extraCount: decrement() });
                                }
                            }
                            return;
                        }
                        case 'mail.channel/unpin':
                            return this._handleNotificationChannelUnpin(message.payload);
                        case 'mail.channel/joined':
                            return this._handleNotificationChannelJoined(message.payload);
                        case 'mail.channel/last_interest_dt_changed':
                            return this._handleNotificationChannelLastInterestDateTimeChanged(message.payload);
                        case 'mail.channel/legacy_insert':
                            return this.messaging.models['Thread'].insert(this.messaging.models['Thread'].convertData({ model: 'mail.channel', ...message.payload }));
                        case 'mail.channel/insert':
                            return this.messaging.models['Channel'].insert(message.payload);
                        case 'mail.guest/insert':
                            return this.messaging.models['Guest'].insert(message.payload);
                        case 'mail.message/insert':
                            return this.messaging.models['Message'].insert(message.payload);
                        case 'mail.channel.rtc.session/insert':
                            return this.messaging.models['RtcSession'].insert(message.payload);
                        case 'mail.channel.rtc.session/peer_notification':
                            return this._handleNotificationRtcPeerToPeer(message.payload);
                        case 'mail.channel/rtc_sessions_update':
                            return this._handleNotificationRtcSessionUpdate(message.payload);
                        case 'mail.channel.rtc.session/ended':
                            return this._handleNotificationRtcSessionEnded(message.payload);
                        case 'mail.thread/insert':
                            return this.messaging.models['Thread'].insert(message.payload);
                        case 'res.users.settings/insert':
                            return this.messaging.models['res.users.settings'].insert(message.payload);
                        case 'res.users.settings.volumes/insert':
                            return this.messaging.models['res.users.settings.volumes'].insert(message.payload);
                        default:
                            return this._handleNotification(message);
                    }
                }
            });
            await Promise.all(proms);
        },
        /**
         * @abstract
         * @private
         * @param {Object} message
         */
        _handleNotification(message) {},
        /**
         * @private
         * @param {Object} payload
         * @param {Object[]} [payload.partners]
         * @param {Object[]|undefined} [payload.guests]
         */
        _handleNotificationBusImStatus({ partners, guests }) {
            if (partners) {
                this.models['Partner'].insert(partners);
            }
            if (guests) {
                this.models['Guest'].insert(guests);
            }
        },
        /**
         * @private
         * @param {Object} payload
         * @param {integer} [payload.id]
         */
        _handleNotificationAttachmentDelete(payload) {
            const attachment = this.messaging.models['Attachment'].findFromIdentifyingData(payload);
            if (attachment) {
                this.messaging.messagingBus.trigger('o-attachment-deleted', { attachment });
                attachment.delete();
            }
        },
        /**
         * @private
         * @param {Object} payload
         * @param {integer} payload.id
         */
        async _handleNotificationChannelDelete({ id }) {
            const channel = this.messaging.models['Thread'].findFromIdentifyingData({
                id,
                model: 'mail.channel',
            });
            if (!channel) {
                return;
            }
            channel.delete();
        },
        /**
         * @private
         * @param {Object} param1
         * @param {integer} param1.channel_id
         * @param {integer} param1.last_message_id
         * @param {integer} param1.partner_id
         */
        async _handleNotificationChannelMemberFetched({
            channel_id: channelId,
            last_message_id,
            partner_id,
        }) {
            const channel = this.messaging.models['Channel'].findFromIdentifyingData({ id: channelId });
            if (!channel) {
                // for example seen from another browser, the current one has no
                // knowledge of the channel
                return;
            }
            if (channel.channel_type === 'channel') {
                // disabled on `channel` channels for performance reasons
                return;
            }
            this.messaging.models['ThreadPartnerSeenInfo'].insert({
                lastFetchedMessage: insert({ id: last_message_id }),
                partner: { id: partner_id },
                thread: channel.thread,
            });
            this.messaging.models['MessageSeenIndicator'].insert({
                message: { id: last_message_id },
                thread: channel.thread,
            });
        },
        /**
         * @private
         * @param {Object} payload
         * @param {Thread} payload.channel
         * @param {integer} [payload.invited_by_user_id]
         * @param {boolean} [payload.open_chat_window] if true, will pin the channel
         */
        _handleNotificationChannelJoined({ channel: channelData, invited_by_user_id: invitedByUserId, open_chat_window: openChatWindow }) {
            const thread = this.messaging.models['Thread'].insert(this.messaging.models['Thread'].convertData(channelData));
            if (this.messaging.currentUser && invitedByUserId !== this.messaging.currentUser.id) {
                // Current user was invited by someone else.
                this.messaging.notify({
                    message: sprintf(
                        this.env._t("You have been invited to #%s"),
                        thread.displayName
                    ),
                    type: 'info',
                });
            }

            if (openChatWindow) {
                // open chat upon being invited (if it was not already opened or folded)
                if (thread.channel.channel_type !== 'channel' && !this.messaging.device.isSmall && !thread.chatWindow) {
                    this.messaging.chatWindowManager.openThread(thread);
                }
            }
        },
        /**
         * @private
         * @param {object} payload
         * @param {integer} payload.id
         * @param {boolean} payload.isServerPinned
         * @param {string} payload.last_interest_dt
         */
        _handleNotificationChannelLastInterestDateTimeChanged({ id, isServerPinned, last_interest_dt }) {
            const channel = this.messaging.models['Thread'].findFromIdentifyingData({
                id: id,
                model: 'mail.channel',
            });
            if (channel) {
                channel.update({
                    lastInterestDateTime: str_to_datetime(last_interest_dt),
                    isServerPinned,
                });
            }
        },
        /**
         * @private
         * @param {Object} payload
         * @param {integer} payload.id
         * @param {Object} payload.messageData
         */
        async _handleNotificationChannelMessage({ id: channelId, message: messageData }) {
            let channel = this.messaging.models['Channel'].findFromIdentifyingData({ id: channelId });
            if (!channel && this.messaging.isCurrentUserGuest) {
                return; // guests should not receive messages for channels they don't know, and they can't make the channel_info RPC
            }
            const convertedData = this.messaging.models['Message'].convertData(messageData);

            // Fetch missing info from channel before going further. Inserting
            // a channel with incomplete info can lead to issues. This is in
            // particular the case with the `uuid` field that is assumed
            // "required" by the rest of the code and is necessary for some
            // features such as chat windows.
            if (!channel || !channel.channel_type) {
                const res = await this.messaging.models['Thread'].performRpcChannelInfo({ ids: [channelId] });
                if (!this.exists()) {
                    return;
                }
                channel = res[0].channel;
            }
            if (!channel.thread.isPinned) {
                channel.thread.pin();
            }

            const message = this.messaging.models['Message'].insert(convertedData);
            this._notifyThreadViewsMessageReceived(message);

            // If the current partner is author, do nothing else.
            if (message.author === this.messaging.currentPartner) {
                return;
            }

            // Chat from OdooBot is considered disturbing and should only be
            // shown on the menu, but no notification and no thread open.
            const isChatWithOdooBot = (
                channel.correspondent &&
                channel.correspondent === this.messaging.partnerRoot
            );
            if (!isChatWithOdooBot) {
                const isOdooFocused = this.env.services['presence'].isOdooFocused();
                // Notify if out of focus
                if (!isOdooFocused && channel.thread.isChatChannel) {
                    this._notifyNewChannelMessageWhileOutOfFocus({
                        channel,
                        message,
                    });
                }
                if (channel.channel_type !== 'channel' && !this.messaging.currentGuest) {
                    // disabled on non-channel threads and
                    // on `channel` channels for performance reasons
                    channel.thread.markAsFetched();
                }
                // open chat on receiving new message if it was not already opened or folded
                if (channel.channel_type !== 'channel' && !this.messaging.device.isSmall && !channel.thread.chatWindow) {
                    this.messaging.chatWindowManager.openThread(channel.thread);
                }
            }
        },
        /**
         * Called when a channel has been seen, and the server responds with the
         * last message seen. Useful in order to track last message seen.
         *
         * @private
         * @param {Object} param1
         * @param {integer} param1.channel_id
         * @param {integer} param1.last_message_id
         * @param {integer} param1.partner_id
         */
        async _handleNotificationChannelMemberSeen({
            channel_id: channelId,
            last_message_id,
            partner_id,
        }) {
            const channel = this.messaging.models['Channel'].findFromIdentifyingData({ id: channelId });
            if (!channel) {
                // for example seen from another browser, the current one has no
                // knowledge of the channel
                return;
            }
            const lastMessage = this.messaging.models['Message'].insert({ id: last_message_id });
            // restrict computation of seen indicator for "non-channel" channels
            // for performance reasons
            const shouldComputeSeenIndicators = channel.channel_type !== 'channel';
            if (shouldComputeSeenIndicators) {
                this.messaging.models['ThreadPartnerSeenInfo'].insert({
                    lastSeenMessage: lastMessage,
                    partner: { id: partner_id },
                    thread: channel.thread,
                });
                this.messaging.models['MessageSeenIndicator'].insert({
                    message: lastMessage,
                    thread: channel.thread,
                });
            }
            if (this.messaging.currentPartner && this.messaging.currentPartner.id === partner_id) {
                channel.thread.update({
                    pendingSeenMessageId: undefined,
                    rawLastSeenByCurrentPartnerMessageId: last_message_id,
                });
            }
        },
        /**
         * @private
         * @param {Object} channelMemberData
         */
        _handleNotificationChannelMemberTypingStatus(channelMemberData) {
            const member = this.messaging.models['ChannelMember'].insert(channelMemberData);
            if (member.isMemberOfCurrentUser) {
                // Ignore management of current persona is typing notification.
                return;
            }
            if (member.isTyping) {
                if (member.channel.thread.typingMembers.includes(member)) {
                    member.channel.thread.refreshOtherMemberTypingMember(member);
                } else {
                    member.channel.thread.registerOtherMemberTypingMember(member);
                }
            } else {
                if (!member.channel.thread.typingMembers.includes(member)) {
                    // Ignore no longer typing notifications of members that
                    // are not registered as typing something.
                    return;
                }
                member.channel.thread.unregisterOtherMemberTypingMember(member);
            }
        },
        /**
         * @private
         * @param {Object} data
         */
        _handleNotificationNeedaction(data) {
            const message = this.messaging.models['Message'].insert(
                this.messaging.models['Message'].convertData(data)
            );
            this.messaging.inbox.update({ counter: increment() });
            const originThread = message.originThread;
            if (originThread && message.isNeedaction) {
                originThread.update({ message_needaction_counter: increment() });
            }
        },
        /**
         * @private
         * @param {Object} data
         * @param {number} data.sender
         * @param {string[]} data.notifications
         */
        _handleNotificationRtcPeerToPeer({ sender, notifications }) {
            for (const content of notifications) {
                this.messaging.rtc.handleNotification(sender, content);
            }
        },
        /**
         * @private
         * @param {Object} param1
         * @param {string} param1.message
         * @param {boolean} param1.message_is_html
         * @param {boolean} param1.sticky
         * @param {string} param1.title
         * @param {boolean} param1.warning
         */
        _handleNotificationSimpleNotification({ message, message_is_html, sticky, title, warning }) {
            this.messaging.notify({
                message: message_is_html ? Markup(message) : message,
                sticky,
                title,
                type: warning ? 'warning' : 'danger',
            });
        },
        /**
         * @private
         * @param {Object} data
         * @param {number} [sessionId]
         */
        async _handleNotificationRtcSessionEnded({ sessionId }) {
            const currentSession = this.messaging.rtc.currentRtcSession;
            if (currentSession && currentSession.id === sessionId) {
                this.messaging.rtc.channel.endCall();
                this.messaging.notify({
                    message: this.env._t("Disconnected from the RTC call by the server"),
                    type: 'warning',
                });
            }
        },
        /**
         * @private
         * @param {Object} data
         * @param {string} [data.id]
         * @param {Object} [data.rtcSessions]
         */
        async _handleNotificationRtcSessionUpdate({ id, rtcSessions }) {
            const channel = this.messaging.models['Thread'].findFromIdentifyingData({ id, model: 'mail.channel' });
            if (!channel) {
                return;
            }
            channel.updateRtcSessions(rtcSessions);
        },
        /**
         * @private
         * @param {Object} param0
         * @param {integer[]} param0.messag_ids
         */
        _handleNotificationMessageDelete({ message_ids }) {
            for (const id of message_ids) {
                const message = this.messaging.models['Message'].findFromIdentifyingData({ id });
                if (message) {
                    message.delete();
                }
            }
        },
        /**
         * @private
         * @param {Object} data
         */
        _handleNotificationPartnerMessageNotificationUpdate({ elements }) {
            for (const messageData of elements) {
                const message = this.messaging.models['Message'].insert(
                    this.messaging.models['Message'].convertData(messageData)
                );
                // implicit: failures are sent by the server as notification
                // only if the current partner is author of the message
                if (!message.author && this.messaging.currentPartner) {
                    message.update({ author: this.messaging.currentPartner });
                }
            }
        },
        /**
         * @private
         * @param {Object} param0
         * @param {integer[]} [param0.message_ids=[]]
         * @param {integer} [param0.needaction_inbox_counter]
         */
        _handleNotificationPartnerMarkAsRead({ message_ids = [], needaction_inbox_counter }) {
            for (const message_id of message_ids) {
                // We need to ignore all not yet known messages because we don't want them
                // to be shown partially as they would be linked directly to cache.
                // Furthermore, server should not send back all message_ids marked as read
                // but something like last read message_id or something like that.
                // (just imagine you mark 1000 messages as read ... )
                const message = this.messaging.models['Message'].findFromIdentifyingData({ id: message_id });
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
            const inbox = this.messaging.inbox;
            if (needaction_inbox_counter !== undefined) {
                inbox.update({ counter: needaction_inbox_counter });
            } else {
                // kept for compatibility in stable
                inbox.update({ counter: decrement(message_ids.length) });
            }
            if (inbox.counter > inbox.thread.cache.fetchedMessages.length) {
                // Force refresh Inbox because depending on what was marked as
                // read the cache might become empty even though there are more
                // messages on the server.
                inbox.thread.cache.update({ hasToLoadMessages: true });
            }
        },
        /**
         * @private
         * @param {Object} param0
         * @param {integer[]} param0.message_ids
         * @param {boolean} param0.starred
         */
        _handleNotificationPartnerToggleStar({ message_ids = [], starred }) {
            const starredMailbox = this.messaging.starred;
            for (const messageId of message_ids) {
                const message = this.messaging.models['Message'].findFromIdentifyingData({
                    id: messageId,
                });
                if (!message) {
                    continue;
                }
                message.update({ isStarred: starred });
                starredMailbox.update({
                    counter: starred ? increment() : decrement(),
                });
            }
        },
        /**
         * On receiving a transient message, i.e. a message which does not come
         * from a member of the channel. Usually a log message, such as one
         * generated from a command with ('/').
         *
         * @private
         * @param {Object} data
         */
        _handleNotificationPartnerTransientMessage(data) {
            const convertedData = this.messaging.models['Message'].convertData(data);
            const lastMessageId = this.messaging.models['Message'].all().reduce(
                (lastMessageId, message) => Math.max(lastMessageId, message.id),
                0
            );
            const partnerRoot = this.messaging.partnerRoot;
            const message = this.messaging.models['Message'].insert(Object.assign(convertedData, {
                author: partnerRoot,
                id: lastMessageId + 0.01,
                isTransient: true,
            }));
            this._notifyThreadViewsMessageReceived(message);
        },
        /**
         * @private
         * @param {Object} payload
         * @param {integer} payload.id
         */
        _handleNotificationChannelLeave({ id }) {
            const thread = this.messaging.models['Thread'].findFromIdentifyingData({
                id,
                model: 'mail.channel',
            });
            if (!thread) {
                return;
            }
            const message = sprintf(this.env._t("You unsubscribed from %s."), thread.displayName);
            this.messaging.notify({ message, type: 'info' });
            // We assume that arriving here the server has effectively
            // unpinned the channel
            thread.update({
                isServerPinned: false,
            });
            if (thread.channel && thread.channel.memberOfCurrentUser) {
                thread.channel.memberOfCurrentUser.delete();
            }
        },
        /**
         * @private
         * @param {Object} payload
         * @param {integer} payload.id
         */
        _handleNotificationChannelUnpin({ id }) {
            const thread = this.messaging.models['Thread'].findFromIdentifyingData({
                id,
                model: 'mail.channel',
            });
            if (!thread) {
                return;
            }
            const message = sprintf(this.env._t("You unpinned your conversation with %s."), thread.displayName);
            this.messaging.notify({ message, type: 'info' });
            // We assume that arriving here the server has effectively
            // unpinned the channel
            thread.update({
                isServerPinned: false,
            });
            if (thread.channel && thread.channel.memberOfCurrentUser) {
                thread.channel.memberOfCurrentUser.delete();
            }
        },
        /**
         * @private
         * @param {Object} payload
         * @param {integer} payload.partnerId
         * @param {string} payload.username
         */
        async _handleNotificationPartnerUserConnection({ partnerId, username }) {
            // If the current user invited a new user, and the new user is
            // connecting for the first time while the current user is present
            // then open a chat for the current user with the new user.
            const message = sprintf(this.env._t('%s connected'), username);
            const title = this.env._t("This is their first connection. Wish them luck.");
            this.messaging.userNotificationManager.sendNotification({ message, title, type: 'info' });
            const chat = await this.messaging.getChat({ partnerId });
            if (!this.exists() || !chat || this.messaging.device.isSmall) {
                return;
            }
            this.messaging.chatWindowManager.openThread(chat.thread);
        },
        /**
         * @private
         * @param {Object} param0
         * @param {Channel} param0.channel
         * @param {Message} param0.message
         */
        _notifyNewChannelMessageWhileOutOfFocus({ channel, message }) {
            const author = message.author;
            const messaging = this.messaging;
            let notificationTitle;
            if (!author) {
                notificationTitle = this.env._t("New message");
            } else {
                if (channel.channel_type === 'channel') {
                    // hack: notification template does not support OWL components,
                    // so we simply use their template to make HTML as if it comes
                    // from component
                    const channelIcon = renderToString('mail.ThreadIcon', {
                        env: this.env,
                        thread: channel.thread,
                    });
                    const channelName = channel.thread.displayName;
                    const channelNameWithIcon = channelIcon + channelName;
                    notificationTitle = sprintf(
                        this.env._t("%s from %s"),
                        author.nameOrDisplayName,
                        channelNameWithIcon
                    );
                } else {
                    notificationTitle = author.nameOrDisplayName;
                }
            }
            const notificationContent = escape(
                htmlToTextContentInline(message.body).substr(0, PREVIEW_MSG_MAX_SIZE)
            );
            this.messaging.userNotificationManager.sendNotification({
                message: notificationContent,
                title: notificationTitle,
                type: 'info',
            });
            messaging.update({ outOfFocusUnreadMessageCounter: increment() });
            const titlePattern = messaging.outOfFocusUnreadMessageCounter === 1
                ? this.env._t("%s Message")
                : this.env._t("%s Messages");
            this.env.services["title"].setParts({
                _chat: sprintf(titlePattern, messaging.outOfFocusUnreadMessageCounter),
            });
        },
        /**
         * Notifies threadViews about the given message being just received.
         * This can allow them adjust their scroll position if applicable.
         *
         * @private
         * @param {Message}
         */
        _notifyThreadViewsMessageReceived(message) {
            for (const thread of message.threads) {
                for (const threadView of thread.threadViews) {
                    threadView.addComponentHint('message-received', { message });
                }
            }
        },
    },
});
