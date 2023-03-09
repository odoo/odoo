/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insert, insertAndUnlink, link, unlink } from '@mail/model/model_field_command';
import { cleanSearchTerm } from '@mail/utils/utils';
import * as mailUtils from '@mail/js/utils';

import { sprintf } from '@web/core/utils/strings';
import { url } from '@web/core/utils/urls';

import { str_to_datetime } from 'web.time';

const getSuggestedRecipientInfoNextTemporaryId = (function () {
    let tmpId = 0;
    return () => {
        tmpId += 1;
        return tmpId;
    };
})();

registerModel({
    name: 'Thread',
    lifecycleHooks: {
        _willDelete() {
            if (this.isTemporary) {
                for (const message of this.messages) {
                    message.delete();
                }
            }
        },
    },
    modelMethods: {
        /**
         * @param {Object} data
         * @return {Object}
         */
        convertData(data) {
            const data2 = {};
            if ('authorizedGroupFullName' in data) {
                data2.authorizedGroupFullName = data.authorizedGroupFullName;
            }
            if ('canPostOnReadonly' in data) {
                data2.canPostOnReadonly = data.canPostOnReadonly;
            }
            if ('channel' in data) {
                data2.channel = data.channel;
                data2.model = 'mail.channel';
            }
            if ('defaultDisplayMode' in data) {
                data2.defaultDisplayMode = data.defaultDisplayMode;
            }
            if ('description' in data) {
                data2.description = data.description;
            }
            if ('model' in data) {
                data2.model = data.model;
            }
            if ('create_uid' in data) {
                data2.creator = insert({ id: data.create_uid });
            }
            if ('group_based_subscription' in data) {
                data2.group_based_subscription = data.group_based_subscription;
            }
            if ('id' in data) {
                data2.id = data.id;
            }
            if ('invitedMembers' in data) {
                data2.invitedMembers = data.invitedMembers;
            }
            if ('is_minimized' in data && 'state' in data) {
                data2.serverFoldState = data.is_minimized ? data.state : 'closed';
            }
            if ('is_pinned' in data) {
                data2.isServerPinned = data.is_pinned;
            }
            if ('last_interest_dt' in data && data.last_interest_dt) {
                data2.lastInterestDateTime = str_to_datetime(data.last_interest_dt);
            }
            if ('last_message' in data && data.last_message) {
                const messageData = this.messaging.models['Message'].convertData({
                    id: data.last_message.id,
                    model: data2.model,
                    res_id: data2.id,
                });
                data2.serverLastMessage = insert(messageData);
            }
            if ('last_message_id' in data && data.last_message_id) {
                const messageData = this.messaging.models['Message'].convertData({
                    id: data.last_message_id,
                    model: data2.model,
                    res_id: data2.id,
                });
                data2.serverLastMessage = insert(messageData);
            }
            if ('message_needaction_counter' in data) {
                data2.message_needaction_counter = data.message_needaction_counter;
            }
            if ('name' in data) {
                data2.name = data.name;
            }
            if ('seen_message_id' in data) {
                data2.rawLastSeenByCurrentPartnerMessageId = data.seen_message_id;
            }
            if ('uuid' in data) {
                data2.uuid = data.uuid;
            }

            // relations
            if ('rtc_inviting_session' in data) {
                data2.rtcInvitingSession = insert(data.rtc_inviting_session);
            }
            if ('rtcSessions' in data) {
                data2.rtcSessions = data.rtcSessions;
            }
            if ('seen_partners_info' in data) {
                if (!data.seen_partners_info) {
                    data2.partnerSeenInfos = clear();
                } else {
                    data2.partnerSeenInfos = data.seen_partners_info.map(
                        ({ fetched_message_id, partner_id, seen_message_id }) => {
                            return {
                                lastFetchedMessage: fetched_message_id ? insert({ id: fetched_message_id }) : clear(),
                                lastSeenMessage: seen_message_id ? insert({ id: seen_message_id }) : clear(),
                                partner: { id: partner_id },
                        };
                    });
                    if (data.id || this.id) {
                        const messageIds = data.seen_partners_info.reduce((currentSet, { fetched_message_id, seen_message_id }) => {
                            if (fetched_message_id) {
                                currentSet.add(fetched_message_id);
                            }
                            if (seen_message_id) {
                                currentSet.add(seen_message_id);
                            }
                            return currentSet;
                        }, new Set());
                        if (messageIds.size > 0) {
                            data2.messageSeenIndicators = [...messageIds].map(messageId => {
                                return {
                                    message: { id: messageId },
                                };
                            });
                        }
                    }
                }
            }

            return data2;
        },
        /**
         * Creates a new group chat with the provided partners.
         *
         * @param {Object} param0
         * @param {number[]} param0.partners_to Ids of the partners to add as channel
         * members.
         * @param {boolean|string} param0.default_display_mode
         * @returns {Thread} The newly created group chat.
         */
        async createGroupChat({ default_display_mode, partners_to }) {
            const channelData = await this.messaging.rpc({
                model: 'mail.channel',
                method: 'create_group',
                kwargs: {
                    default_display_mode,
                    partners_to,
                },
            });
            return this.messaging.models['Thread'].insert(
                this.messaging.models['Thread'].convertData(channelData)
            );
        },
        /**
         * Fetches threads matching the given composer search state to extend
         * the JS knowledge and to update the suggestion list accordingly.
         * More specifically only thread of model 'mail.channel' are fetched.
         *
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {Thread} [options.thread] prioritize and/or restrict
         *  result in the context of given thread
         */
        async fetchSuggestions(searchTerm, { thread } = {}) {
            const channelsData = await this.messaging.rpc(
                {
                    model: 'mail.channel',
                    method: 'get_mention_suggestions',
                    kwargs: { search: searchTerm },
                },
                { shadow: true },
            );
            this.messaging.models['Thread'].insert(channelsData.map(channelData =>
                this.messaging.models['Thread'].convertData(channelData)
            ));
        },
        /**
         * Returns a sort function to determine the order of display of threads
         * in the suggestion list.
         *
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {Thread} [options.thread] prioritize result in the
         *  context of given thread
         * @returns {function}
         */
        getSuggestionSortFunction(searchTerm, { thread } = {}) {
            const cleanedSearchTerm = cleanSearchTerm(searchTerm);
            return (a, b) => {
                const isAPublicChannel = a.model === 'mail.channel' && a.channel.channel_type === 'channel' && (!a.authorizedGroupFullName);
                const isBPublicChannel = b.model === 'mail.channel' && b.channel.channel_type === 'channel' && (!b.authorizedGroupFullName);
                if (isAPublicChannel && !isBPublicChannel) {
                    return -1;
                }
                if (!isAPublicChannel && isBPublicChannel) {
                    return 1;
                }
                const isMemberOfA = a.channel && a.channel.memberOfCurrentUser;
                const isMemberOfB = b.channel && b.channel.memberOfCurrentUser;
                if (isMemberOfA && !isMemberOfB) {
                    return -1;
                }
                if (!isMemberOfA && isMemberOfB) {
                    return 1;
                }
                const cleanedAName = cleanSearchTerm(a.name || '');
                const cleanedBName = cleanSearchTerm(b.name || '');
                if (cleanedAName.startsWith(cleanedSearchTerm) && !cleanedBName.startsWith(cleanedSearchTerm)) {
                    return -1;
                }
                if (!cleanedAName.startsWith(cleanedSearchTerm) && cleanedBName.startsWith(cleanedSearchTerm)) {
                    return 1;
                }
                if (cleanedAName < cleanedBName) {
                    return -1;
                }
                if (cleanedAName > cleanedBName) {
                    return 1;
                }
                return a.id - b.id;
            };
        },
        /**
         * Load the previews of the specified threads. Basically, it fetches the
         * last messages, since they are used to display inline content of them.
         *
         * @param {Thread[]} threads
         */
        async loadPreviews(threads) {
            const channelIds = threads.reduce((list, thread) => {
                if (thread.model === 'mail.channel') {
                    return list.concat(thread.id);
                }
                return list;
            }, []);
            if (channelIds.length === 0) {
                return;
            }
            const channelPreviews = await this.messaging.rpc({
                model: 'mail.channel',
                method: 'channel_fetch_preview',
                args: [channelIds],
            }, { shadow: true });
            this.messaging.models['Message'].insert(channelPreviews.filter(p => p.last_message).map(
                channelPreview => this.messaging.models['Message'].convertData(channelPreview.last_message)
            ));
        },
        /**
         * Performs the `channel_fold` RPC on `mail.channel`.
         *
         * @param {number} channelId
         * @param {string} state
         */
        async performRpcChannelFold(channelId, state) {
            return this.messaging.rpc({
                model: 'mail.channel',
                method: 'channel_fold',
                args: [[channelId]],
                kwargs: {
                    state,
                }
            }, { shadow: true });
        },
        /**
         * Performs the `channel_info` RPC on `mail.channel`.
         *
         * @param {Object} param0
         * @param {integer[]} param0.ids list of id of channels
         * @returns {Thread[]}
         */
        async performRpcChannelInfo({ ids }) {
            const channelInfos = await this.messaging.rpc({
                model: 'mail.channel',
                method: 'channel_info',
                args: [ids],
            }, { shadow: true });
            const channels = this.messaging.models['Thread'].insert(
                channelInfos.map(channelInfo => this.messaging.models['Thread'].convertData(channelInfo))
            );
            return channels;
        },
        /**
         * Performs the `/mail/channel/set_last_seen_message` RPC.
         *
         * @param {Object} param0
         * @param {integer} param0.id id of channel
         * @param {integer[]} param0.lastMessageId
         */
        async performRpcChannelSeen({ id, lastMessageId }) {
            return this.messaging.rpc({
                route: `/mail/channel/set_last_seen_message`,
                params: {
                    channel_id: id,
                    last_message_id: lastMessageId,
                },
            }, { shadow: true });
        },
        /**
         * Performs the `channel_pin` RPC on `mail.channel`.
         *
         * @param {Object} param0
         * @param {number} param0.channelId
         * @param {boolean} [param0.pinned=false]
         */
        async performRpcChannelPin({ channelId, pinned = false }) {
            return this.messaging.rpc({
                model: 'mail.channel',
                method: 'channel_pin',
                args: [[channelId]],
                kwargs: {
                    pinned,
                },
            }, { shadow: true });
        },
        /**
         * Performs the `channel_create` RPC on `mail.channel`.
         *
         * @param {Object} param0
         * @param {string} param0.name
         * @param {integer} param0.group_id
         * @returns {Thread} the created channel
         */
        async performRpcCreateChannel({ name, group_id }) {
            const data = await this.messaging.rpc({
                model: 'mail.channel',
                method: 'channel_create',
                args: [name, group_id],
            });
            return this.messaging.models['Thread'].insert(
                this.messaging.models['Thread'].convertData(data)
            );
        },
        /**
         * Search for thread matching `searchTerm`.
         *
         * @param {Object} param0
         * @param {integer} param0.limit
         * @param {string} param0.searchTerm
         */
        async searchChannelsToOpen({ limit, searchTerm }) {
            const domain = [
                ['channel_type', '=', 'channel'],
                ['name', 'ilike', searchTerm],
            ];
            const fields = ['channel_type', 'name'];
            const channelsData = await this.messaging.rpc({
                model: "mail.channel",
                method: "search_read",
                kwargs: {
                    domain,
                    fields,
                    limit,
                },
            });
            return this.insert(channelsData.map(channelData =>
                this.messaging.models['Thread'].convertData({
                    channel: {
                        channel_type: channelData.channel_type,
                        id: channelData.id,
                    },
                    id: channelData.id,
                    name: channelData.name,
                })
            ));
        },
        /**
         * Returns threads that match the given search term. More specially only
         * threads of model 'mail.channel' are suggested, and if the context
         * thread is a private channel, only itself is returned if it matches
         * the search term.
         *
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {Thread} [options.thread] prioritize and/or restrict
         *  result in the context of given thread
         * @returns {[mail.threads[], mail.threads[]]}
         */
        searchSuggestions(searchTerm, { thread } = {}) {
            let threads;
            if (thread && thread.model === 'mail.channel' && (thread.channel.channel_type !== 'channel' || (thread.channel.channel_type === 'channel' && thread.authorizedGroupFullName))) {
                // Only return the current channel when in the context of a
                // group restricted channel or group or chat. Indeed, the message with the mention
                // would appear in the target channel, so this prevents from
                // inadvertently leaking the private message into the mentioned
                // channel.
                threads = [thread];
            } else {
                threads = this.messaging.models['Thread'].all();
            }
            const cleanedSearchTerm = cleanSearchTerm(searchTerm);
            return [threads.filter(thread =>
                !thread.isTemporary &&
                thread.channel &&
                thread.channel.channel_type === 'channel' &&
                thread.displayName &&
                cleanSearchTerm(thread.displayName).includes(cleanedSearchTerm)
            )];
        },
    },
    recordMethods: {
        /**
         * Changes description of the thread to the given new description.
         * Only makes sense for channels.
         *
         * @param {string} description
         */
        async changeDescription(description) {
            this.update({ description });
            return this.messaging.rpc({
                model: 'mail.channel',
                method: 'channel_change_description',
                args: [[this.id]],
                kwargs: { description },
            });
        },
        /**
         * Client-side ending of the call.
         */
        endCall() {
            if (this.rtc) {
                this.rtc.reset();
                this.messaging.soundEffects.channelLeave.play();
            }
            this.update({
                rtc: clear(),
                rtcInvitingSession: clear(),
            });
        },
        /**
         * Requests the given `requestList` data from the server.
         *
         * @param {string[]} requestList
         */
        async fetchData(requestList) {
            if (this.isTemporary) {
                return;
            }
            const requestSet = new Set(requestList);
            if (!this.hasActivities) {
                requestSet.delete('activities');
            }
            if (requestSet.has('attachments')) {
                this.update({ isLoadingAttachments: true });
            }
            if (requestSet.has('messages')) {
                this.cache.loadNewMessages();
            }
            const {
                activities: activitiesData,
                attachments: attachmentsData,
                canPostOnReadonly,
                followers: followersData,
                hasWriteAccess,
                mainAttachment,
                hasReadAccess,
                suggestedRecipients: suggestedRecipientsData,
            } = await this.messaging.rpc({
                route: '/mail/thread/data',
                params: {
                    request_list: [...requestSet],
                    thread_id: this.id,
                    thread_model: this.model,
                },
            }, { shadow: true });
            if (!this.exists()) {
                return;
            }
            const values = { canPostOnReadonly, hasWriteAccess, mainAttachment, hasReadAccess };
            if (activitiesData) {
                Object.assign(values, {
                    activities: activitiesData.map(activityData =>
                        this.messaging.models['Activity'].convertData(activityData)
                    ),
                });
            }
            if (attachmentsData) {
                Object.assign(values, {
                    areAttachmentsLoaded: true,
                    isLoadingAttachments: false,
                    originThreadAttachments: attachmentsData,
                });
            }
            if (followersData) {
                Object.assign(values, {
                    followers: followersData.map(followerData =>
                        this.messaging.models['Follower'].convertData(followerData)
                    ),
                });
            }
            if (suggestedRecipientsData) {
                const recipientInfoList = suggestedRecipientsData.map(recipientInfoData => {
                    const [partner_id, emailInfo, lang, reason] = recipientInfoData;
                    const [name, email] = emailInfo && mailUtils.parseEmail(emailInfo);
                    return {
                        email,
                        id: getSuggestedRecipientInfoNextTemporaryId(),
                        name,
                        lang,
                        partner: partner_id ? insert({ id: partner_id }) : clear(),
                        reason,
                    };
                });
                Object.assign(values, {
                    suggestedRecipientInfoList: recipientInfoList,
                });
            }
            this.update(values);
            this.messaging.messagingBus.trigger('o-thread-loaded-data', { thread: this });
        },
        /**
         * Add current user to provided thread's followers.
         */
        async follow() {
            await this.messaging.rpc({
                model: this.model,
                method: 'message_subscribe',
                args: [[this.id]],
                kwargs: {
                    partner_ids: [this.messaging.currentPartner.id],
                },
            });
            if (!this.exists()) {
                return;
            }
            this.fetchData(['followers', 'suggestedRecipients']);
        },
        /**
         * Performs the rpc to leave the rtc call of the channel.
         */
        async performRpcLeaveCall() {
            await this.messaging.rpc({
                route: '/mail/rtc/channel/leave_call',
                params: { channel_id: this.id },
            }, { shadow: true });
        },
        /**
         * Leaves the current call if there is one, joins the call if the user was
         * not yet in it.
         *
         * @param {Object} options
         */
        async toggleCall(options) {
            this.update({ hasPendingRtcRequest: true });
            const isActiveCall = !!this.rtc;
            if (this.messaging.rtc.channel) {
                await this.messaging.rtc.channel.leaveCall();
            }
            if (isActiveCall) {
                this.update({ hasPendingRtcRequest: false });
                return;
            }
            await this._joinCall(options);
            this.update({ hasPendingRtcRequest: false });
        },
        /**
         * @param {Object} [param0]
         * @param {boolean} [param0.startWithVideo] whether or not to start the call with the video
         * @param {boolean} [param0.videoType] type of the video: 'user-video' or 'display'
         */
        async _joinCall({ startWithVideo = false, videoType } = {}) {
            if (this.model !== 'mail.channel') {
                return;
            }
            if (!this.messaging.device.hasRtcSupport) {
                this.messaging.notify({
                    message: this.env._t("Your browser does not support webRTC."),
                    type: 'warning',
                });
                return;
            }
            const { rtcSessions, iceServers, sessionId, invitedMembers } = await this.messaging.rpc({
                route: '/mail/rtc/channel/join_call',
                params: {
                    channel_id: this.id,
                    check_rtc_session_ids: this.rtcSessions.map(rtcSession => rtcSession.id),
                },
            }, { shadow: true });
            if (!this.exists()) {
                return;
            }
            this.update({
                rtc: this.messaging.rtc,
                rtcInvitingSession: clear(),
                rtcSessions,
                invitedMembers,
            });
            await this.messaging.rtc.initSession({
                currentSessionId: sessionId,
                iceServers,
                startWithAudio: true,
                startWithVideo,
                videoType,
            });
            if (!this.exists()) {
                return;
            }
            this.messaging.soundEffects.channelJoin.play();
        },
        /**
         * Notifies the server and does the cleanup of the current call.
         */
        async leaveCall() {
            await this.performRpcLeaveCall();
            this.endCall();
        },
        /**
         * @param {Array<Object>} rtcSessions server representation of the current rtc sessions of the channel
         */
        updateRtcSessions(rtcSessions) {
            const oldCount = this.rtcSessions.length;
            this.update({ rtcSessions });
            if (this.rtc) {
                const newCount = this.rtcSessions.length;
                if (newCount > oldCount) {
                    this.messaging.soundEffects.channelJoin.play();
                }
                if (newCount < oldCount) {
                    this.messaging.soundEffects.memberLeave.play();
                }
            }
            this.rtc && this.rtc.filterCallees(this.rtcSessions);
            if (this.rtc && !this.rtc.currentRtcSession) {
                this.endCall();
            }
        },
        /**
         * Returns the name of the given persona in the context of this thread.
         *
         * @param {Persona} persona
         * @returns {string}
         */
        getMemberName(persona) {
            return persona.name;
        },
        /**
         * Joins this thread. Only makes sense on channels of type channel.
         */
        async join() {
            await this.messaging.rpc({
                model: 'mail.channel',
                method: 'add_members',
                args: [[this.id]],
                kwargs: { partner_ids: [this.messaging.currentPartner.id] }
            });
        },
        /**
         * Leaves this thread. Only makes sense on channels of type channel.
         */
        async leave() {
            await this.messaging.rpc({
                model: 'mail.channel',
                method: 'action_unfollow',
                args: [[this.id]],
            });
        },
        /**
         * Mark the specified conversation as fetched.
         */
        async markAsFetched() {
            await this.messaging.rpc({
                model: 'mail.channel',
                method: 'channel_fetched',
                args: [[this.id]],
            }, { shadow: true });
        },
        /**
         * Mark the specified conversation as read/seen.
         *
         * @param {Message} message the message to be considered as last seen.
         */
        async markAsSeen(message) {
            if (this.messaging.currentGuest) {
                return;
            }
            if (this.model !== 'mail.channel') {
                return;
            }
            if (this.pendingSeenMessageId && message.id <= this.pendingSeenMessageId) {
                return;
            }
            if (
                this.lastSeenByCurrentPartnerMessageId &&
                message.id <= this.lastSeenByCurrentPartnerMessageId
            ) {
                return;
            }
            this.update({ pendingSeenMessageId: message.id });
            return this.messaging.models['Thread'].performRpcChannelSeen({
                id: this.id,
                lastMessageId: message.id,
            });
        },
        /**
         * Marks as read all needaction messages with this thread as origin.
         */
        async markNeedactionMessagesAsOriginThreadAsRead() {
            await this.messaging.models['Message'].markAsRead(this.needactionMessagesAsOriginThread);
        },
        /**
         * Notifies the server of new fold state. Useful for initial,
         * cross-tab, and cross-device chat window state synchronization.
         *
         * @param {string} state
         */
        async notifyFoldStateToServer(state) {
            if (this.model !== 'mail.channel') {
                // Server sync of fold state is only supported for channels.
                return;
            }
            return this.messaging.models['Thread'].performRpcChannelFold(this.id, state);
        },
        /**
         * Notify server to leave the current channel. Useful for cross-tab
         * and cross-device chat window state synchronization.
         *
         * Only makes sense if isPendingPinned is set to the desired value.
         */
        async notifyPinStateToServer() {
            if (this.channel.channel_type === 'channel') {
                await this.leave();
                return;
            }
            await this.messaging.models['Thread'].performRpcChannelPin({
                channelId: this.id,
                pinned: this.isPendingPinned,
            });
        },
        /**
         * Opens this thread either as form view, in discuss app, or as a chat
         * window. The thread will be opened in an "active" matter, which will
         * interrupt current user flow.
         *
         * @param {Object} [param0]
         * @param {boolean} [param0.expanded=false]
         * @param {boolean} [param0.focus]
         */
        async open({ expanded = false, focus } = {}) {
            const discuss = this.messaging.discuss;
            // check if thread must be opened in form view
            if (!this.channel && !this.mailbox) {
                if (expanded || discuss.discussView) {
                    // Close chat window because having the same thread opened
                    // both in chat window and as main document does not look
                    // good.
                    this.messaging.chatWindowManager.closeThread(this);
                    await this.messaging.openDocument({
                        id: this.id,
                        model: this.model,
                    });
                    return;
                }
            }
            // check if thread must be opened in discuss
            if (
                (!this.messaging.device.isSmall && (discuss.discussView || expanded)) ||
                this.mailbox
            ) {
                return discuss.openThread(this, {
                    focus: focus !== undefined ? focus : !this.messaging.device.isMobileDevice,
                });
            }
            // thread must be opened in chat window
            return this.messaging.chatWindowManager.openThread(this, {
                makeActive: true,
            });
        },
        /**
         * Opens the most appropriate view that is a profile for this thread.
         */
        async openProfile() {
            return this.messaging.openDocument({
                id: this.id,
                model: this.model,
            });
        },
        /**
         * Pin this thread and notify server of the change.
         */
        async pin() {
            this.update({ isPendingPinned: true });
            if (this.messaging.currentGuest) {
                return;
            }
            await this.notifyPinStateToServer();
        },
        /**
         * Refresh the typing status of the current partner.
         */
        refreshCurrentPartnerIsTyping() {
            this.update({
                currentPartnerInactiveTypingTimer: { doReset: this.currentPartnerInactiveTypingTimer ? true : undefined },
            });
        },
        /**
         * Called to refresh a registered other member that is typing something.
         *
         * @param {Member} member
         */
        refreshOtherMemberTypingMember(member) {
            this.messaging.models['OtherMemberLongTypingInThreadTimer'].insert({
                member,
                thread: this,
                timer: {
                    doReset: true,
                },
            });
        },
        /**
         * Called when current partner is inserting some input in composer.
         * Useful to notify current partner is currently typing something in the
         * composer of this thread to all other members.
         */
        async registerCurrentPartnerIsTyping() {
            // Handling of typing timers.
            this.update({
                currentPartnerInactiveTypingTimer: {},
                currentPartnerLongTypingTimer: {},
            });
            // Manage typing member relation.
            const memberOfCurrentUser = this.channel.memberOfCurrentUser;
            const newOrderedTypingMembers = [
                ...this.orderedTypingMembers.filter(member => member !== memberOfCurrentUser),
                memberOfCurrentUser,
            ];
            this.update({
                isCurrentPartnerTyping: true,
                orderedTypingMembers: newOrderedTypingMembers,
                typingMembers: link(memberOfCurrentUser),
            });
            // Notify typing status to other members.
            await this.throttleNotifyCurrentPartnerTypingStatus.do();
        },
        /**
         * Called to register a new other member partner is typing something.
         *
         * @param {Member} member
         */
        registerOtherMemberTypingMember(member) {
            this.update({ otherMembersLongTypingTimers: insert({ member }) });
            const newOrderedTypingMembers = [
                ...this.orderedTypingMembers.filter(currentMember => currentMember !== member),
                member,
            ];
            this.update({
                orderedTypingMembers: newOrderedTypingMembers,
                typingMembers: link(member),
            });
        },
        /**
         * Renames this thread to the given new name.
         * Only makes sense for channels.
         *
         * @param {string} name
         */
        async rename(name) {
            this.update({ name });
            return this.messaging.rpc({
                model: 'mail.channel',
                method: 'channel_rename',
                args: [[this.id]],
                kwargs: { name },
            });
        },
        /**
         * Sets the custom name of this thread for the current user to the given
         * new name.
         * Only makes sense for channels.
         *
         * @param {string} newName
         */
        async setCustomName(newName) {
            return this.messaging.rpc({
                model: 'mail.channel',
                method: 'channel_set_custom_name',
                args: [this.id],
                kwargs: { name: newName },
            });
        },
        /**
         * @param {Attachment} attachment
         */
        async setMainAttachment(attachment) {
            this.update({ mainAttachment: attachment });
            await this.messaging.rpc({
                model: 'ir.attachment',
                method: 'register_as_main_attachment',
                args: [[this.mainAttachment.id]],
            });
        },
        /**
         * Unfollow current partner from this thread.
         */
        async unfollow() {
            await this.followerOfCurrentPartner.remove();
        },
        /**
         * Unpin this thread and notify server of the change.
         */
        async unpin() {
            this.update({ isPendingPinned: false });
            if (this.messaging.currentGuest) {
                return;
            }
            await this.notifyPinStateToServer();
        },
        /**
         * Called when current partner has explicitly stopped inserting some
         * input in composer. Useful to notify current partner has currently
         * stopped typing something in the composer of this thread to all other
         * members.
         *
         * @param {Object} [param0={}]
         * @param {boolean} [param0.immediateNotify=false] if set, is typing
         *   status of current partner is immediately notified and doesn't
         *   consume throttling at all.
         */
        unregisterCurrentPartnerIsTyping({ immediateNotify = false } = {}) {
            // Handling of typing timers.
            this.update({
                currentPartnerInactiveTypingTimer: clear(),
                currentPartnerLongTypingTimer: clear(),
            });
            // Manage typing member relation.
            const memberOfCurrentUser = this.channel.memberOfCurrentUser;
            const newOrderedTypingMembers = this.orderedTypingMembers.filter(member => member !== memberOfCurrentUser);
            this.update({
                isCurrentPartnerTyping: false,
                orderedTypingMembers: newOrderedTypingMembers,
                typingMembers: memberOfCurrentUser ? unlink(memberOfCurrentUser) : undefined,
            });
            // Notify typing status to other members.
            if (immediateNotify) {
                this.throttleNotifyCurrentPartnerTypingStatus.clear();
            }
            this.throttleNotifyCurrentPartnerTypingStatus.do();
        },
        /**
         * Called to unregister an other member partner that is no longer typing
         * something.
         *
         * @param {Member} member
         */
        unregisterOtherMemberTypingMember(member) {
            this.update({ otherMembersLongTypingTimers: insertAndUnlink({ member }) });
            const newOrderedTypingMembers = this.orderedTypingMembers.filter(currentMember => currentMember !== member);
            this.update({
                orderedTypingMembers: newOrderedTypingMembers,
                typingMembers: unlink(member),
            });
        },
        /**
         * Unsubscribe current user from provided channel.
         */
        unsubscribe() {
            this.leaveCall();
            this.messaging.chatWindowManager.closeThread(this);
            this.unpin();
        },
        /**
         * @private
         */
        async _notifyCurrentPartnerTypingStatus() {
            if (
                this.forceNotifyNextCurrentPartnerTypingStatus ||
                this.isCurrentPartnerTyping !== this.currentPartnerLastNotifiedIsTyping
            ) {
                if (this.model === 'mail.channel') {
                    await this.messaging.rpc({
                        route: '/mail/channel/notify_typing',
                        params: {
                            'channel_id': this.id,
                            'is_typing': this.isCurrentPartnerTyping,
                        },
                    }, { shadow: true });
                    if (!this.exists()) {
                        return;
                    }
                }
                if (this.isCurrentPartnerTyping && this.currentPartnerLongTypingTimer) {
                    this.currentPartnerLongTypingTimer.update({ doReset: true });
                }
            }
            this.update({
                currentPartnerLastNotifiedIsTyping: this.isCurrentPartnerTyping,
                forceNotifyNextCurrentPartnerTypingStatus: false,
            });
        },
        /**
         * @private
         */
        _onChangeLastSeenByCurrentPartnerMessageId() {
            this.messaging.messagingBus.trigger('o-thread-last-seen-by-current-partner-message-id-changed', {
                thread: this,
            });
        },
        /**
         * Handles change of pinned state coming from the server. Useful to
         * clear pending state once server acknowledged the change.
         *
         * @private
         * @see isPendingPinned
         */
        _onIsServerPinnedChanged() {
            if (this.isServerPinned === this.isPendingPinned) {
                this.update({ isPendingPinned: clear() });
            }
        },
        /**
         * Handles change of fold state coming from the server. Useful to
         * synchronize corresponding chat window.
         *
         * @private
         */
        _onServerFoldStateChanged() {
            if (!this.messaging.chatWindowManager) {
                // avoid crash during destroy
                return;
            }
            if (this.messaging.device.isSmall) {
                return;
            }
            if (this.serverFoldState === 'closed') {
                this.messaging.chatWindowManager.closeThread(this, {
                    notifyServer: false,
                });
            } else {
                this.messaging.chatWindowManager.openThread(this, {
                    isFolded: this.serverFoldState === 'folded',
                    notifyServer: false,
                });
            }
        },
        /**
         * Event handler for clicking thread in discuss app.
         */
        async onClick() {
            await this.open();
        },
        onCurrentPartnerInactiveTypingTimeout() {
            this.unregisterCurrentPartnerIsTyping();
        },
        /**
         * Called when current partner has been typing for a very long time.
         * Immediately notify other members that he/she is still typing.
         */
        async onCurrentPartnerLongTypingTimeout() {
            this.update({
                currentPartnerLongTypingTimer: clear(),
                forceNotifyNextCurrentPartnerTypingStatus: true,
                isCurrentPartnerTyping: true,
            });
            this.throttleNotifyCurrentPartnerTypingStatus.clear();
            await this.throttleNotifyCurrentPartnerTypingStatus.do();
        },
    },
    fields: {
        accessRestrictedToGroupText: attr({
            compute() {
                if (!this.authorizedGroupFullName) {
                    return clear();
                }
                return sprintf(
                    this.env._t('Access restricted to group "%(groupFullName)s"'),
                    { 'groupFullName': this.authorizedGroupFullName }
                );
            },
            default: '',
        }),
        /**
         * Determines the `mail.activity` that belong to `this`, assuming `this`
         * has activities (@see hasActivities).
         */
        activities: many('Activity', {
            inverse: 'thread',
        }),
        activity_state: attr({
            compute() {
                if (this.overdueActivities.length > 0) {
                    return 'overdue';
                }
                if (this.todayActivities.length > 0) {
                    return 'today';
                }
                if (this.futureActivities.length > 0) {
                    return 'planned';
                }
                return clear();
            },
        }),
        allAttachments: many('Attachment', {
            compute() {
                const allAttachments = [...new Set(this.originThreadAttachments.concat(this.attachments))]
                    .sort((a1, a2) => {
                        // "uploading" before "uploaded" attachments.
                        if (!a1.isUploading && a2.isUploading) {
                            return 1;
                        }
                        if (a1.isUploading && !a2.isUploading) {
                            return -1;
                        }
                        // "most-recent" before "oldest" attachments.
                        return Math.abs(a2.id) - Math.abs(a1.id);
                    });
                return allAttachments;
            },
            inverse: 'allThreads',
        }),
        areAttachmentsLoaded: attr({
            default: false,
        }),
        attachments: many('Attachment', {
            inverse: 'threads',
        }),
        attachmentsInWebClientView: many('Attachment', {
            inverse: 'threadsAsAttachmentsInWebClientView',
            readonly: true,
            sort: [['greater-first', 'id']],
        }),
        authorizedGroupFullName: attr(),
        cache: one('ThreadCache', {
            default: {},
            inverse: 'thread',
            readonly: true,
            required: true,
        }),
        canPostOnReadonly: attr({
            default: false,
        }),
        channel: one('Channel', {
            inverse: 'thread',
            isCausal: true,
            readonly: true,
        }),
        /**
         * States the chat window related to this thread (if any).
         */
        chatWindow: one('ChatWindow', {
            inverse: 'thread',
        }),
        /**
         * Determines the composer state of this thread.
         */
        composer: one('Composer', {
            compute() {
                if (this.mailbox) {
                    return clear();
                }
                return {};
            },
            inverse: 'thread',
        }),
        creator: one('User'),
        /**
         * Timer of current partner that was currently typing something, but
         * there is no change on the input for 5 seconds. This is used
         * in order to automatically notify other members that current
         * partner has stopped typing something, due to making no changes
         * on the composer for some time.
         */
        currentPartnerInactiveTypingTimer: one('Timer', {
            inverse: 'threadAsCurrentPartnerInactiveTypingTimerOwner',
        }),
        /**
         * Last 'is_typing' status of current partner that has been notified
         * to other members. Useful to prevent spamming typing notifications
         * to other members if it hasn't changed. An exception is the
         * current partner long typing scenario where current partner has
         * to re-send the same typing notification from time to time, so
         * that other members do not assume he/she is no longer typing
         * something from not receiving any typing notifications for a
         * very long time.
         *
         * Supported values: true/false/undefined.
         * undefined makes only sense initially and during current partner
         * long typing timeout flow.
         */
        currentPartnerLastNotifiedIsTyping: attr(),
        /**
         * Timer of current partner that is typing a very long text. When
         * the other members do not receive any typing notification for a
         * long time, they must assume that the related partner is no longer
         * typing something (e.g. they have closed the browser tab).
         * This is a timer to let other members know that current partner
         * is still typing something, so that they should not assume he/she
         * has stopped typing something.
         */
        currentPartnerLongTypingTimer: one('Timer', {
            inverse: 'threadAsCurrentPartnerLongTypingTimerOwner',
        }),
        /**
         * Determines the default display mode of this channel. Should contain
         * either no value (to display the chat), or 'video_full_screen' to
         * start a call in full screen.
         */
        defaultDisplayMode: attr(),
        /**
         * States the description of this thread. Only applies to channels.
         */
        description: attr(),
        displayName: attr({
            compute() {
                if (this.channel) {
                    return this.channel.displayName;
                }
                if (this.mailbox) {
                    return this.mailbox.name;
                }
                return this.name;
            },
        }),
        fetchMessagesParams: attr({
            compute() {
                if (this.model === 'mail.channel') {
                    return { 'channel_id': this.id };
                }
                if (this.mailbox) {
                    return {};
                }
                return {
                    'thread_id': this.id,
                    'thread_model': this.model,
                };
            },
        }),
        fetchMessagesUrl: attr({
            compute() {
                if (this.model === 'mail.channel') {
                    return `/mail/channel/messages`;
                }
                if (this.mailbox) {
                    return this.mailbox.fetchMessagesUrl;
                }
                return `/mail/thread/messages`;
            },
        }),
        followerOfCurrentPartner: one('Follower', {
            inverse: 'followedThreadAsFollowerOfCurrentPartner',
        }),
        followersPartner: many('Partner', {
            related: 'followers.partner',
        }),
        followers: many('Follower', {
            inverse: 'followedThread',
        }),
        /**
         * Determines whether the next request to notify current partner
         * typing status should always result to making RPC, regardless of
         * whether last notified current partner typing status is the same.
         * Most of the time we do not want to notify if value hasn't
         * changed, exception being the long typing scenario of current
         * partner.
         */
        forceNotifyNextCurrentPartnerTypingStatus: attr({
            default: false,
        }),
        /**
         * States the `Activity` that belongs to `this` and that are
         * planned in the future (due later than today).
         */
        futureActivities: many('Activity', {
            compute() {
                return this.activities.filter(activity => activity.state === 'planned');
            },
        }),
        group_based_subscription: attr({
            default: false,
        }),
        /**
         * States whether the current user has read access for this thread.
         */
        hasReadAccess: attr(),
        /**
         * States whether `this` has activities (`mail.activity.mixin` server side).
         */
        hasActivities: attr({
            default: false,
        }),
        /**
         * Determines whether the RTC call feature should be displayed.
         */
        hasCallFeature: attr({
            compute() {
                if (!this.channel) {
                    return clear();
                }
                return ['channel', 'chat', 'group'].includes(this.channel.channel_type);
            },
        }),
        /**
         * States whether this thread should has the invite feature. Only makes
         * sense for channels.
         */
        hasInviteFeature: attr({
            compute() {
                return this.model === 'mail.channel';
            },
        }),
        /**
         * Determines whether it makes sense for this thread to have a member list.
         */
        hasMemberListFeature: attr({
            compute() {
                if (!this.channel) {
                    return clear();
                }
                return ['channel', 'group'].includes(this.channel.channel_type);
            },
        }),
        /**
         * States whether there is a server request for joining or leaving the RTC session.
         * TODO Should maybe be on messaging (after messaging env rebase) to lock the rpc across all threads.
         */
        hasPendingRtcRequest: attr({
            default: false,
        }),
        /**
         * Determine whether this thread has the seen indicators (V and VV)
         * enabled or not.
         */
        hasSeenIndicators: attr({
            compute() {
                if (!this.channel) {
                    return clear();
                }
                return ['chat', 'livechat'].includes(this.channel.channel_type);
            },
            default: false,
        }),
        /**
         * States whether current user has write access for the record. If yes, few other operations
         * (like adding other followers to the thread) are enabled for the user.
         */
        hasWriteAccess: attr({
            default: false,
        }),
        id: attr({
            identifying: true,
        }),
        invitationLink: attr({
            compute() {
                if (!this.channel) {
                    return clear();
                }
                if (!this.uuid || !this.channel.channel_type || this.channel.channel_type === 'chat') {
                    return clear();
                }
                return `${window.location.origin}/chat/${this.id}/${this.uuid}`;
            },
        }),
        /**
         * List of members that have been invited to the RTC call of this channel.
         */
        invitedMembers: many('ChannelMember'),
        /**
         * Determines whether this description can be changed.
         * Only makes sense for channels.
         */
        isChannelDescriptionChangeable: attr({
            compute() {
                if (!this.channel) {
                    return clear();
                }
                return ['channel', 'group'].includes(this.channel.channel_type);
            },
        }),
        /**
         * Determines whether this thread can be renamed.
         * Only makes sense for channels.
         */
        isChannelRenamable: attr({
            compute() {
                if (!this.channel) {
                    return clear();
                }
                return ['chat', 'channel', 'group'].includes(this.channel.channel_type);
            },
        }),
        /**
         * States whether this thread is a `mail.channel` qualified as chat.
         *
         * Useful to list chat channels, like in messaging menu with the filter
         * 'chat'.
         */
        isChatChannel: attr({
            compute() {
                if (!this.channel) {
                    return clear();
                }
                return ['chat', 'group'].includes(this.channel.channel_type);
            },
            default: false,
        }),
        isCurrentPartnerFollowing: attr({
            compute() {
                return this.followers.some(follower =>
                    follower.partner && follower.partner === this.messaging.currentPartner
                );
            },
            default: false,
        }),
        isCurrentPartnerTyping: attr({
            default: false,
        }),
        /**
         * States whether this thread description is editable by the current user.
         */
        isDescriptionEditableByCurrentUser: attr({
            compute() {
                return Boolean(
                    this.messaging &&
                    this.messaging.currentUser &&
                    this.messaging.currentUser.isInternalUser &&
                    this.isChannelDescriptionChangeable
                );
            },
        }),
        /**
         * States whether `this` is currently loading attachments.
         */
        isLoadingAttachments: attr({
            default: false,
        }),
        /**
         * Determine if there is a pending pin state change, which is a change
         * of pin state requested by the client but not yet confirmed by the
         * server.
         *
         * This field can be updated to immediately change the pin state on the
         * interface and to notify the server of the new state.
         */
        isPendingPinned: attr(),
        /**
         * Boolean that determines whether this thread is pinned
         * in discuss and present in the messaging menu.
         */
        isPinned: attr({
            compute() {
                return this.isPendingPinned !== undefined ? this.isPendingPinned : this.isServerPinned;
            },
        }),
        /**
         * Determine the last pin state known by the server, which is the pin
         * state displayed after initialization or when the last pending
         * pin state change was confirmed by the server.
         *
         * This field should be considered read only in most situations. Only
         * the code handling pin state change from the server should typically
         * update it.
         */
        isServerPinned: attr({
            default: false,
        }),
        isTemporary: attr({
            default: false,
        }),
        /**
         * States the date and time of the last interesting event that happened
         * in this channel for this partner. This includes: creating, joining,
         * pinning, and new message posted. It is contained as a Date object.
         */
        lastInterestDateTime: attr(),
        lastCurrentPartnerMessageSeenByEveryone: one('Message', {
            compute() {
                const otherPartnerSeenInfos =
                    this.partnerSeenInfos.filter(partnerSeenInfo =>
                        partnerSeenInfo.partner !== this.messaging.currentPartner);
                if (otherPartnerSeenInfos.length === 0) {
                    return clear();
                }

                const otherPartnersLastSeenMessageIds =
                    otherPartnerSeenInfos.map(partnerSeenInfo =>
                        partnerSeenInfo.lastSeenMessage ? partnerSeenInfo.lastSeenMessage.id : 0
                    );
                if (otherPartnersLastSeenMessageIds.length === 0) {
                    return clear();
                }
                const lastMessageSeenByAllId = Math.min(
                    ...otherPartnersLastSeenMessageIds
                );
                const currentPartnerOrderedSeenMessages =
                    this.orderedNonTransientMessages.filter(message =>
                        message.author === this.messaging.currentPartner &&
                        message.id <= lastMessageSeenByAllId);

                if (
                    !currentPartnerOrderedSeenMessages ||
                    currentPartnerOrderedSeenMessages.length === 0
                ) {
                    return clear();
                }
                return currentPartnerOrderedSeenMessages.slice().pop();
            },
        }),
        /**
         * Last message of the thread, could be a transient one.
         */
        lastMessage: one('Message', {
            compute() {
                const {
                    length: l,
                    [l - 1]: lastMessage,
                } = this.orderedMessages;
                if (lastMessage) {
                    return lastMessage;
                }
                return clear();
            },
        }),
        /**
         * States the last known needaction message having this thread as origin.
         */
        lastNeedactionMessageAsOriginThread: one('Message', {
            compute() {
                const orderedNeedactionMessagesAsOriginThread = this.needactionMessagesAsOriginThread.sort(
                    (m1, m2) => m1.id < m2.id ? -1 : 1
                );
                const {
                    length: l,
                    [l - 1]: lastNeedactionMessageAsOriginThread,
                } = orderedNeedactionMessagesAsOriginThread;
                if (lastNeedactionMessageAsOriginThread) {
                    return lastNeedactionMessageAsOriginThread;
                }
                return clear();
            },
        }),
        /**
         * Last non-transient message.
         */
        lastNonTransientMessage: one('Message', {
            compute() {
                const {
                    length: l,
                    [l - 1]: lastMessage,
                } = this.orderedNonTransientMessages;
                if (lastMessage) {
                    return lastMessage;
                }
                return clear();
            },
        }),
        /**
         * Last seen message id of the channel by current partner.
         *
         * Also, it needs to be kept as an id because it's considered like a "date" and could stay
         * even if corresponding message is deleted. It is basically used to know which
         * messages are before or after it.
         */
        lastSeenByCurrentPartnerMessageId: attr({
            /**
             * Adjusts the last seen message received from the server to consider
             * the following messages also as read if they are either transient
             * messages or messages from the current partner.
             */
            compute() {
                const firstMessage = this.orderedMessages[0];
                if (
                    firstMessage &&
                    this.rawLastSeenByCurrentPartnerMessageId &&
                    this.rawLastSeenByCurrentPartnerMessageId < firstMessage.id
                ) {
                    // no deduction can be made if there is a gap
                    return this.rawLastSeenByCurrentPartnerMessageId;
                }
                let lastSeenByCurrentPartnerMessageId = this.rawLastSeenByCurrentPartnerMessageId;
                for (const message of this.orderedMessages) {
                    if (message.id <= this.rawLastSeenByCurrentPartnerMessageId) {
                        continue;
                    }
                    if (
                        (message.author && this.messaging.currentPartner && message.author === this.messaging.currentPartner) ||
                        (message.guestAuthor && this.messaging.currentGuest && message.guestAuthor === this.messaging.currentGuest) ||
                        message.isTransient
                    ) {
                        lastSeenByCurrentPartnerMessageId = message.id;
                        continue;
                    }
                    return lastSeenByCurrentPartnerMessageId;
                }
                return lastSeenByCurrentPartnerMessageId;
            },
            default: 0,
        }),
        mailbox: one('Mailbox', {
            inverse: 'thread',
        }),
        mainAttachment: one('Attachment'),
        /**
         * Determines the last mentioned channels of the last composer related
         * to this thread. Useful to sync the composer when re-creating it.
         */
        mentionedChannelsBackup: many('Thread'),
        /**
         * Determines the last mentioned partners of the last composer related
         * to this thread. Useful to sync the composer when re-creating it.
         */
        mentionedPartnersBackup: many('Partner'),
        /**
         * Determines the message before which the "new message" separator must
         * be positioned, if any.
         */
        messageAfterNewMessageSeparator: one('Message', {
            compute() {
                if (!this.channel) {
                    return clear();
                }
                if (this.channel.localMessageUnreadCounter === 0) {
                    return clear();
                }
                const index = this.orderedMessages.findIndex(message =>
                    message.id === this.lastSeenByCurrentPartnerMessageId
                );
                if (index === -1) {
                    return clear();
                }
                const message = this.orderedMessages[index + 1];
                if (!message) {
                    return clear();
                }
                return message;
            },
        }),
        message_needaction_counter: attr({
            default: 0,
        }),
        /**
         * All messages that this thread is linked to.
         * Note that this field is automatically computed by inverse
         * computed field.
         */
        messages: many('Message', {
            inverse: 'threads',
            readonly: true,
        }),
        /**
         * All messages that have been originally posted in this thread.
         */
        messagesAsOriginThread: many('Message', {
            inverse: 'originThread',
            isCausal: true,
        }),
        /**
         * Contains the message fetched/seen indicators for all messages of this thread.
         */
        messageSeenIndicators: many('MessageSeenIndicator', {
            inverse: 'thread',
        }),
        messagingAsAllCurrentClientThreads: one('Messaging', {
            compute() {
                if (!this.messaging || !this.channel || !this.channel.memberOfCurrentUser || !this.isServerPinned) {
                    return clear();
                }
                return this.messaging;
            },
            inverse: 'allCurrentClientThreads',
        }),
        messagingAsRingingThread: one('Messaging', {
            compute() {
                if (this.rtcInvitingSession) {
                    return this.messaging;
                }
                return clear();
            },
            inverse: 'ringingThreads',
        }),
        messagingMenuAsPinnedAndUnreadChannel: one('MessagingMenu', {
            compute() {
                if (!this.messaging || !this.messaging.messagingMenu) {
                    return clear();
                }
                if (this.channel && this.isPinned && this.channel.localMessageUnreadCounter > 0) {
                    return this.messaging.messagingMenu;
                }
                return clear();
            },
            inverse: 'pinnedAndUnreadChannels',
        }),
        model: attr({
            identifying: true,
        }),
        model_name: attr(),
        moduleIcon: attr(),
        name: attr(),
        /**
         * States all known needaction messages having this thread as origin.
         */
        needactionMessagesAsOriginThread: many('Message', {
            compute() {
                return this.messagesAsOriginThread.filter(message => message.isNeedaction);
            },
        }),
        /**
         * All messages ordered like they are displayed.
         */
        orderedMessages: many('Message', {
            compute() {
                return this.messages.sort((m1, m2) => m1.id < m2.id ? -1 : 1);
            },
        }),
        /**
         * All messages ordered like they are displayed. This field does not
         * contain transient messages which are not "real" records.
         */
        orderedNonTransientMessages: many('Message', {
            compute() {
                return this.orderedMessages.filter(m => !m.isTransient);
            },
        }),
        /**
         * Ordered typing members on this thread, excluding the current partner.
         */
        orderedOtherTypingMembers: many('ChannelMember', {
            compute() {
                return this.orderedTypingMembers.filter(member => !member.isMemberOfCurrentUser);
            },
        }),
        /**
         * Ordered list of typing members.
         */
        orderedTypingMembers: many('ChannelMember'),
        originThreadAttachments: many('Attachment', {
            inverse: 'originThread',
            isCausal: true,
        }),
        /**
         * Registry of timers of partners currently typing in the thread,
         * excluding current partner. This is useful in order to
         * automatically unregister typing members when not receive any
         * typing notification after a long time. Timers are internally
         * indexed by partner records as key. The current partner is
         * ignored in this registry of timers.
         *
         * @see registerOtherMemberTypingMember
         * @see unregisterOtherMemberTypingMember
         */
        otherMembersLongTypingTimers: many('OtherMemberLongTypingInThreadTimer', {
            inverse: 'thread',
        }),
        /**
         * States the `Activity` that belongs to `this` and that are
         * overdue (due earlier than today).
         */
        overdueActivities: many('Activity', {
            compute() {
                return this.activities.filter(activity => activity.state === 'overdue');
            },
        }),
        /**
         * Contains the seen information for all members of the thread.
         * FIXME This field should be readonly once task-2336946 is done.
         */
        partnerSeenInfos: many('ThreadPartnerSeenInfo', {
            inverse: 'thread',
        }),
        /**
         * Determine if there is a pending seen message change, which is a change
         * of seen message requested by the client but not yet confirmed by the
         * server.
         */
        pendingSeenMessageId: attr(),
        rawLastSeenByCurrentPartnerMessageId: attr({
            default: 0,
        }),
        /**
         * If set, the current thread is the thread that hosts the current RTC call.
         */
        rtc: one('Rtc', {
            inverse: 'channel',
        }),
        callInviteRequestPopup: one('CallInviteRequestPopup', {
            compute() {
                if (this.rtcInvitingSession) {
                    return {};
                }
                return clear();
            },
            inverse: 'thread',
        }),
        /**
         * The session that invited the current user, it is only set when the
         * invitation is still pending.
         */
        rtcInvitingSession: one('RtcSession', {
            inverse: 'calledChannels',
        }),
        rtcSessions: many('RtcSession', {
            inverse: 'channel',
            isCausal: true,
        }),
        /**
         * Determine the last fold state known by the server, which is the fold
         * state displayed after initialization or when the last pending
         * fold state change was confirmed by the server.
         *
         * This field should be considered read only in most situations. Only
         * the code handling fold state change from the server should typically
         * update it.
         */
        serverFoldState: attr({
            default: 'closed',
        }),
        /**
         * Last message considered by the server.
         *
         * Useful to compute localMessageUnreadCounter field.
         *
         * @see localMessageUnreadCounter
         */
        serverLastMessage: one('Message'),
        suggestable: one('ComposerSuggestable', {
            default: {},
            inverse: 'thread',
            readonly: true,
            required: true,
        }),
        /**
         * Determines the `SuggestedRecipientInfo` concerning `this`.
         */
        suggestedRecipientInfoList: many('SuggestedRecipientInfo', {
            inverse: 'thread',
            isCausal: true,
        }),
        /**
         * Determines the last content of the last composer related to this
         * thread. Useful to sync the composer when re-creating it.
         */
        textInputContentBackup: attr({
            default: "",
        }),
        /**
         * Determines the last cursor end of the last composer related to this
         * thread. Useful to sync the composer when re-creating it.
         */
        textInputCursorEndBackup: attr({
            default: 0,
        }),
        /**
         * Determines the last cursor start of the last composer related to this
         * thread. Useful to sync the composer when re-creating it.
         */
        textInputCursorStartBackup: attr({
            default: 0,
        }),
        /**
         * Determines the last selection direction of the last composer related
         * to this thread. Useful to sync the composer when re-creating it.
         */
        textInputSelectionDirectionBackup: attr({
            default: "none",
        }),
        threadViews: many('ThreadView', {
            inverse: 'thread',
        }),
        /**
         * Clearable and cancellable throttled version of the
         * `_notifyCurrentPartnerTypingStatus` method.
         * This is useful when the current partner posts a message and
         * types something else afterwards: it must notify immediately that
         * he/she is typing something, instead of waiting for the throttle
         * internal timer.
         *
         * @see _notifyCurrentPartnerTypingStatus
         */
        throttleNotifyCurrentPartnerTypingStatus: one('Throttle', {
            compute() {
                return {
                    func: () => this._notifyCurrentPartnerTypingStatus(),
                };
            },
            inverse: 'threadAsThrottleNotifyCurrentPartnerTypingStatus',
        }),
        /**
         * States the `Activity` that belongs to `this` and that are due
         * specifically today.
         */
        todayActivities: many('Activity', {
            compute() {
                return this.activities.filter(activity => activity.state === 'today');
            },
        }),
        threadNeedactionPreviewViews: many('ThreadNeedactionPreviewView', {
            inverse: 'thread',
        }),
        /**
         * Members that are currently typing something in the composer of this
         * thread, including current partner.
         */
        typingMembers: many('ChannelMember'),
        /**
         * Text that represents the status on this thread about typing members.
         */
        typingStatusText: attr({
            compute() {
                if (this.orderedOtherTypingMembers.length === 0) {
                    return clear();
                }
                if (this.orderedOtherTypingMembers.length === 1) {
                    return sprintf(
                        this.env._t("%s is typing..."),
                        this.getMemberName(this.orderedOtherTypingMembers[0].persona)
                    );
                }
                if (this.orderedOtherTypingMembers.length === 2) {
                    return sprintf(
                        this.env._t("%s and %s are typing..."),
                        this.getMemberName(this.orderedOtherTypingMembers[0].persona),
                        this.getMemberName(this.orderedOtherTypingMembers[1].persona)
                    );
                }
                return sprintf(
                    this.env._t("%s, %s and more are typing..."),
                    this.getMemberName(this.orderedOtherTypingMembers[0].persona),
                    this.getMemberName(this.orderedOtherTypingMembers[1].persona)
                );
            },
            default: '',
        }),
        /**
         * URL to access to the conversation.
         */
        url: attr({
            /**
             * Compute an url string that can be used inside a href attribute
             */
            compute() {
                const baseHref = url('/web');
                if (this.model === 'mail.channel') {
                    return `${baseHref}#action=mail.action_discuss&active_id=${this.model}_${this.id}`;
                }
                return `${baseHref}#model=${this.model}&id=${this.id}`;
            },
            default: '',
        }),
        uuid: attr(),
        /**
         * The amount of videos broadcast in the current Rtc call
         */
        videoCount: attr({
            compute() {
                return this.rtcSessions.filter(session => session.videoStream).length;
            },
            default: 0,
        }),
    },
    onChanges: [
        {
            dependencies: ['lastSeenByCurrentPartnerMessageId'],
            methodName: '_onChangeLastSeenByCurrentPartnerMessageId',
        },
        {
            dependencies: ['isServerPinned'],
            methodName: '_onIsServerPinnedChanged',
        },
        {
            dependencies: ['serverFoldState'],
            methodName: '_onServerFoldStateChanged',
        },
    ],
});
