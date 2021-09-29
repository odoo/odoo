/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { decrement, increment, insert, insertAndReplace, link, replace, unlink } from '@mail/model/model_field_command';
import { htmlToTextContentInline } from '@mail/js/utils';

import { str_to_datetime } from 'web.time';

const PREVIEW_MSG_MAX_SIZE = 350; // optimal for native English speakers

function factory(dependencies) {

    class MessagingNotificationHandler extends dependencies['mail.model'] {

        /**
         * @override
         */
        _willDelete() {
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
                if (typeof message === 'object') {
                    switch (message.type) {
                        case 'mail.attachment_delete':
                            return this._handleNotificationAttachmentDelete(message.payload);
                        case 'mail.channel_description_change':
                            return this._handleNotificationChannelDescriptionChanged(message.payload);
                        case 'mail.channel_joined':
                            return this._handleNotificationChannelJoined(message.payload);
                        case 'mail.channel_last_interest_dt_changed':
                            return this._handleNotificationChannelLastInterestDateTimeChanged(message.payload);
                        case 'mail.channel_rename':
                            return this._handleNotificationChannelRenamed(message.payload);
                        case 'mail.channel_update':
                            return this._handleNotificationChannelUpdate(message.payload);
                        case 'mail.guest_update':
                            return this.messaging.models['mail.guest'].insert(message.payload);
                        case 'mail.message_update':
                            return this.messaging.models['mail.message'].insert(message.payload);
                        case 'mail.rtc_session_update':
                            return this.messaging.models['mail.rtc_session'].insert(message.payload);
                        case 'res.users_settings_changed':
                            return this._handleNotificationResUsersSettings(message.payload);
                        case 'rtc_peer_notification':
                            return this._handleNotificationRtcPeerToPeer(message.payload);
                        case 'rtc_incoming_invitation_update':
                            return this._handleNotificationRtcInvitation(message.payload);
                        case 'rtc_sessions_update':
                            return this._handleNotificationRtcSessionUpdate(message.payload);
                        case 'rtc_session_ended':
                            return this._handleNotificationRtcSessionEnded(message.payload);
                        case 'res_users_settings_volumes_update':
                            return this._handleNotificationVolumeSettingUpdate(message.payload);
                    }
                }
                const [, model, id] = channel;
                switch (model) {
                    case 'ir.needaction':
                        return this._handleNotificationNeedaction(message);
                    case 'mail.channel':
                        return this._handleNotificationChannel(id, message);
                    case 'res.partner':
                        if (id !== this.messaging.currentPartner.id) {
                            // ignore broadcast to other partners
                            return;
                        }
                        return this._handleNotificationPartner(Object.assign({}, message));
                }
            });
            await this.async(() => Promise.all(proms));
        }


        /**
         * @private
         * @param {Object} payload
         * @param {integer} [payload.id]
         */
        _handleNotificationAttachmentDelete(payload) {
            const attachment = this.messaging.models['mail.attachment'].findFromIdentifyingData(payload);
            if (attachment) {
                attachment.delete();
            }
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
                partner_name,
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
                        partner_name,
                    });
                default:
                    return this._handleNotificationChannelMessage(channelId, data);
            }
        }

        /**
         * @private
         * @param {Object} payload
         * @param {integer} payload.id
         * @param {String} payload.description
         */
        _handleNotificationChannelDescriptionChanged({ id, description }) {
            const channel = this.messaging.models['mail.thread'].insert({
                id,
                model: 'mail.channel',
            });
            channel.update({ description });
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
            const channel = this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: channelId,
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
            this.messaging.models['mail.thread_partner_seen_info'].insert({
                lastFetchedMessage: insert({ id: last_message_id }),
                partner: insertAndReplace({ id: partner_id }),
                thread: replace(channel),
            });
            this.messaging.models['mail.message_seen_indicator'].insert({
                message: insertAndReplace({ id: last_message_id }),
                thread: replace(channel),
            });
            // FIXME force the computing of message values (cf task-2261221)
            this.messaging.models['mail.message_seen_indicator'].recomputeFetchedValues(channel);
        }

        /**
         * @private
         * @param {Object} payload
         * @param {mail.thread} payload.channel
         * @param {integer} payload.invited_by_user_id
         */
        _handleNotificationChannelJoined({ channel: channelData, invited_by_user_id: invitedByUserId }) {
            const channel = this.messaging.models['mail.thread'].insert(this.messaging.models['mail.thread'].convertData(channelData));
            if (invitedByUserId !== this.messaging.currentUser.id) {
                // Current user was invited by someone else.
                this.env.services['notification'].notify({
                    message: _.str.sprintf(
                        this.env._t("You have been invited to #%s"),
                        channel.name
                    ),
                    type: 'info',
                });
            }
        }

        /**
         * @private
         * @param {Object} payload
         * @param {integer} payload.id
         * @param {String} payload.name
         */
        _handleNotificationChannelRenamed({ id, name }) {
            const channel = this.messaging.models['mail.thread'].insert({
                id,
                model: 'mail.channel',
            });
            channel.update({ name });
        }

        /**
         * @private
         * @param {object} payload
         * @param {integer} payload.id
         * @param {string} payload.last_interest_dt
         */
        _handleNotificationChannelLastInterestDateTimeChanged({ id, last_interest_dt }) {
            const channel = this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: id,
                model: 'mail.channel',
            });
            if (channel) {
                channel.update({
                    lastInterestDateTime: str_to_datetime(last_interest_dt),
                });
            }
        }

        /**
         * @private
         * @param {integer} channelId
         * @param {Object} messageData
         */
        async _handleNotificationChannelMessage(channelId, messageData) {
            let channel = this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: channelId,
                model: 'mail.channel',
            });
            if (!channel && this.messaging.isCurrentUserGuest) {
                return; // guests should not receive messages for channels they don't know, and they can't make the channel_info RPC
            }
            const wasChannelExisting = !!channel;
            const convertedData = this.messaging.models['mail.message'].convertData(messageData);

            // Fetch missing info from channel before going further. Inserting
            // a channel with incomplete info can lead to issues. This is in
            // particular the case with the `uuid` field that is assumed
            // "required" by the rest of the code and is necessary for some
            // features such as chat windows.
            if (!channel) {
                channel = (await this.async(() =>
                    this.messaging.models['mail.thread'].performRpcChannelInfo({ ids: [channelId] })
                ))[0];
            }
            if (!channel.isPinned) {
                channel.pin();
            }

            const message = this.messaging.models['mail.message'].insert(convertedData);
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
                const isOdooFocused = this.env.services['bus_service'].isOdooFocused();
                // Notify if out of focus
                if (!isOdooFocused && channel.isChatChannel) {
                    this._notifyNewChannelMessageWhileOutOfFocus({
                        channel,
                        message,
                    });
                }
                if (channel.model === 'mail.channel' && channel.channel_type !== 'channel' && !this.messaging.currentGuest) {
                    // disabled on non-channel threads and
                    // on `channel` channels for performance reasons
                    channel.markAsFetched();
                }
                // open chat on receiving new message if it was not already opened or folded
                if (channel.channel_type !== 'channel' && !this.messaging.device.isMobile && !channel.chatWindow) {
                    this.messaging.chatWindowManager.openThread(channel);
                }
            }

            // If the channel wasn't known its correct counter was fetched at
            // the start of the method, no need update it here.
            if (!wasChannelExisting) {
                return;
            }
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
            guest_id,
        }) {
            const channel = this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: channelId,
                model: 'mail.channel',
            });
            if (!channel) {
                // for example seen from another browser, the current one has no
                // knowledge of the channel
                return;
            }
            const lastMessage = this.messaging.models['mail.message'].insert({ id: last_message_id });
            // restrict computation of seen indicator for "non-channel" channels
            // for performance reasons
            const shouldComputeSeenIndicators = channel.channel_type !== 'channel';
            if (shouldComputeSeenIndicators) {
                this.messaging.models['mail.thread_partner_seen_info'].insert({
                    lastSeenMessage: link(lastMessage),
                    partner: insertAndReplace({ id: partner_id }),
                    thread: replace(channel),
                });
                this.messaging.models['mail.message_seen_indicator'].insert({
                    message: replace(lastMessage),
                    thread: replace(channel),
                });
            }
            if (this.messaging.currentPartner && this.messaging.currentPartner.id === partner_id) {
                channel.update({
                    lastSeenByCurrentPartnerMessageId: last_message_id,
                    pendingSeenMessageId: undefined,
                });
            }
            if (shouldComputeSeenIndicators) {
                // FIXME force the computing of thread values (cf task-2261221)
                this.messaging.models['mail.thread'].computeLastCurrentPartnerMessageSeenByEveryone(channel);
                // FIXME force the computing of message values (cf task-2261221)
                this.messaging.models['mail.message_seen_indicator'].recomputeSeenValues(channel);
            }
        }

        /**
         * @private
         * @param {integer} channelId
         * @param {Object} param1
         * @param {boolean} param1.is_typing
         * @param {integer} param1.partner_id
         * @param {string} param1.partner_name
         */
        _handleNotificationChannelTypingStatus(channelId, { is_typing, partner_id, partner_name }) {
            const channel = this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: channelId,
                model: 'mail.channel',
            });
            if (!channel) {
                return;
            }
            const partner = this.messaging.models['mail.partner'].insert({
                id: partner_id,
                name: partner_name,
            });
            if (partner === this.messaging.currentPartner) {
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
         * @param {Object} channelData
         */
        _handleNotificationChannelUpdate(channelData) {
            this.messaging.models['mail.thread'].insert({ model: 'mail.channel', ...channelData });
        }

        /**
         * @private
         * @param {object} settings
         * @param {boolean} settings.use_push_to_talk
         * @param {String} settings.push_to_talk_key
         * @param {number} settings.voice_active_duration
         * @param {boolean} [settings.is_discuss_sidebar_category_channel_open]
         * @param {boolean} [settings.is_discuss_sidebar_category_chat_open]
         * @param {Object} [payload.volume_settings]
         */
        _handleNotificationResUsersSettings(settings) {
            if ('is_discuss_sidebar_category_channel_open' in settings) {
                this.messaging.discuss.categoryChannel.update({
                    isServerOpen: settings.is_discuss_sidebar_category_channel_open,
                });
            }
            if ('is_discuss_sidebar_category_chat_open' in settings) {
                this.messaging.discuss.categoryChat.update({
                    isServerOpen: settings.is_discuss_sidebar_category_chat_open,
                });
            }
            this.messaging.userSetting.update({
                usePushToTalk: settings.use_push_to_talk,
                pushToTalkKey: settings.push_to_talk_key,
                voiceActiveDuration: settings.voice_active_duration,
                volumeSettings: settings.volume_settings && insert(settings.volume_settings.map(volumeSetting => this.messaging.models['mail.volume_setting'].convertData(volumeSetting))),
            });
        }

        /**
         * @private
         * @param {Object} data
         */
        _handleNotificationNeedaction(data) {
            const message = this.messaging.models['mail.message'].insert(
                this.messaging.models['mail.message'].convertData(data)
            );
            this.messaging.inbox.update({ counter: increment() });
            const originThread = message.originThread;
            if (originThread && message.isNeedaction) {
                originThread.update({ message_needaction_counter: increment() });
            }
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
                return this._handleNotificationChannelSeen(data.channel_id, data);
            } else if (type === 'deletion') {
                return this._handleNotificationPartnerDeletion(data);
            } else if (type === 'message_notification_update') {
                return this._handleNotificationPartnerMessageNotificationUpdate(data.elements);
            } else if (type === 'mark_as_read') {
                return this._handleNotificationPartnerMarkAsRead(data);
            } else if (type === 'simple_notification') {
                this.env.services['notification'].notify({
                    message: data.message,
                    sticky: data.sticky,
                    messageIsHtml: data.message_is_html,
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
            } else if (!type) {
                return this._handleNotificationPartnerChannel(data);
            }
        }

        /**
         * @private
         * @param {Object} data
         * @param {string} data.channelId
         * @param {string} [data.rtcSession]
         */
        async _handleNotificationRtcInvitation({ channelId, rtcSession }) {
            const channel = this.messaging.models['mail.thread'].findFromIdentifyingData({ id: channelId, model: 'mail.channel' });
            if (!channel) {
                return;
            }
            if (channel.rtc) {
                return;
            }
            if (rtcSession) {
                return channel.update({ rtcInvitingSession: insert(this.messaging.models['mail.rtc_session'].convertData(rtcSession)) });
            }
            return channel.update({ rtcInvitingSession: unlink() });
        }

        /**
         * @private
         * @param {Object} data
         * @param {string} data.sender
         * @param {string[]} data.notifications
         */
        _handleNotificationRtcPeerToPeer({ sender, notifications }) {
            for (const content of notifications) {
                this.messaging.rtc.handleNotification(sender, content);
            }
        }

        /**
         * @private
         * @param {Object} data
         * @param {Object} [data.volumeSettings]
         */
        async _handleNotificationVolumeSettingUpdate({ volumeSettings }) {
            this.messaging && this.messaging.userSetting.update({
                volumeSettings: volumeSettings,
            });
        }

        /**
         * @private
         * @param {Object} data
         * @param {number} [sessionId]
         */
        async _handleNotificationRtcSessionEnded({ sessionId }) {
            const currentSession = this.messaging.rtc.currentRtcSession;
            if (currentSession && currentSession.id === sessionId) {
                this.messaging.rtc.channel.endCall();
                this.env.services['notification'].notify({
                    message: this.env._t("Disconnected from the RTC call by the server"),
                    type: 'warning',
                });
            }
        }

        /**
         * @private
         * @param {Object} data
         * @param {string} [data.id]
         * @param {Object} [data.rtcSessions]
         */
        async _handleNotificationRtcSessionUpdate({ id, rtcSessions }) {
            const channel = this.messaging.models['mail.thread'].findFromIdentifyingData({ id, model: 'mail.channel' });
            if (!channel) {
                return;
            }
            channel.updateRtcSessions(rtcSessions);
        }

        /**
         * @private
         * @param {Object} data
         * @param {Object} data.message
         */
        _handleNotificationPartnerAuthor(data) {
            this.messaging.models['mail.message'].insert(
                this.messaging.models['mail.message'].convertData(data.message)
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
            const convertedData = this.messaging.models['mail.thread'].convertData(
                Object.assign({ model: 'mail.channel' }, data)
            );
            if (!convertedData.members) {
                // channel_info does not return all members of channel for
                // performance reasons, but code is expecting to know at
                // least if the current partner is member of it.
                // (e.g. to know when to display "invited" notification)
                // Current partner can always be assumed to be a member of
                // channels received through this notification.
                convertedData.members = link(this.messaging.currentPartner);
            }
            let channel = this.messaging.models['mail.thread'].findFromIdentifyingData(convertedData);
            const wasCurrentPartnerMember = (
                channel &&
                channel.members.includes(this.messaging.currentPartner)
            );

            channel = this.messaging.models['mail.thread'].insert(convertedData);
            if (
                channel.channel_type === 'channel' &&
                data.info !== 'creation' &&
                !wasCurrentPartnerMember
            ) {
                this.env.services['notification'].notify({
                    message: _.str.sprintf(
                        this.env._t("You have been invited to: %s"),
                        channel.name
                    ),
                    type: 'info',
                });
            }
            // a new thread with unread messages could have been added
        }

        /**
         * @private
         * @param {Object} param0
         * @param {integer[]} param0.messag_ids
         */
        _handleNotificationPartnerDeletion({ message_ids }) {
            for (const id of message_ids) {
                const message = this.messaging.models['mail.message'].findFromIdentifyingData({ id });
                if (message) {
                    message.delete();
                }
            }
            // deleting message might have deleted notifications, force recompute
            this.messaging.notificationGroupManager.computeGroups();
        }

        /**
         * @private
         * @param {Object} data
         */
        _handleNotificationPartnerMessageNotificationUpdate(data) {
            for (const messageData of data) {
                const message = this.messaging.models['mail.message'].insert(
                    this.messaging.models['mail.message'].convertData(messageData)
                );
                // implicit: failures are sent by the server as notification
                // only if the current partner is author of the message
                if (!message.author && this.messaging.currentPartner) {
                    message.update({ author: link(this.messaging.currentPartner) });
                }
            }
            this.messaging.notificationGroupManager.computeGroups();
        }

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
                const message = this.messaging.models['mail.message'].findFromIdentifyingData({ id: message_id });
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
            if (inbox.counter > inbox.cache.fetchedMessages.length) {
                // Force refresh Inbox because depending on what was marked as
                // read the cache might become empty even though there are more
                // messages on the server.
                inbox.cache.update({ hasToLoadMessages: true });
            }
        }

        /**
         * @private
         * @param {Object} param0
         * @param {integer[]} param0.message_ids
         * @param {boolean} param0.starred
         */
        _handleNotificationPartnerToggleStar({ message_ids = [], starred }) {
            const starredMailbox = this.messaging.starred;
            for (const messageId of message_ids) {
                const message = this.messaging.models['mail.message'].findFromIdentifyingData({
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
            const convertedData = this.messaging.models['mail.message'].convertData(data);
            const lastMessageId = this.messaging.models['mail.message'].all().reduce(
                (lastMessageId, message) => Math.max(lastMessageId, message.id),
                0
            );
            const partnerRoot = this.messaging.partnerRoot;
            const message = this.messaging.models['mail.message'].create(Object.assign(convertedData, {
                author: link(partnerRoot),
                id: lastMessageId + 0.01,
                isTransient: true,
            }));
            this._notifyThreadViewsMessageReceived(message);
        }

        /**
         * @private
         * @param {integer} channelId
         */
        _handleNotificationPartnerUnsubscribe(channelId) {
            const channel = this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: channelId,
                model: 'mail.channel',
            });
            if (!channel) {
                return;
            }
            let message;
            if (channel.correspondent) {
                const correspondent = channel.correspondent;
                message = _.str.sprintf(
                    this.env._t("You unpinned your conversation with <b>%s</b>."),
                    correspondent.name
                );
            } else {
                message = _.str.sprintf(
                    this.env._t("You unsubscribed from <b>%s</b>."),
                    channel.name
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
         * @param {Object} param0
         * @param {string} param0.message
         * @param {integer} param0.partner_id
         * @param {string} param0.title
         */
        async _handleNotificationPartnerUserConnection({ message, partner_id, title }) {
            // If the current user invited a new user, and the new user is
            // connecting for the first time while the current user is present
            // then open a chat for the current user with the new user.
            this.env.services['bus_service'].sendNotification({ message, title, type: 'info' });
            const chat = await this.async(() =>
                this.messaging.getChat({ partnerId: partner_id }
            ));
            if (!chat || this.messaging.device.isMobile) {
                return;
            }
            this.messaging.chatWindowManager.openThread(chat);
        }

        /**
         * @private
         * @param {Object} param0
         * @param {mail.thread} param0.channel
         * @param {mail.message} param0.message
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
                    const channelIcon = this.env.qweb.renderToString('mail.ThreadIcon', {
                        env: this.env,
                        thread: channel,
                    });
                    const channelName = channel.displayName;
                    const channelNameWithIcon = channelIcon + channelName;
                    notificationTitle = _.str.sprintf(
                        this.env._t("%s from %s"),
                        author.nameOrDisplayName,
                        channelNameWithIcon
                    );
                } else {
                    notificationTitle = author.nameOrDisplayName;
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
    MessagingNotificationHandler.identifyingFields = ['messaging'];
    MessagingNotificationHandler.modelName = 'mail.messaging_notification_handler';

    return MessagingNotificationHandler;
}

registerNewModel('mail.messaging_notification_handler', factory);
