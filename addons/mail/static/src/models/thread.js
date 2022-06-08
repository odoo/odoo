/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insert, insertAndReplace, insertAndUnlink, link, replace, unlink } from '@mail/model/model_field_command';
import { OnChange } from '@mail/model/model_onchange';
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
    identifyingFields: ['model', 'id'],
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
            if ('avatarCacheKey' in data) {
                data2.avatarCacheKey = data.avatarCacheKey;
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
            if ('channel_type' in data) {
                data2.channel_type = data.channel_type;
                data2.model = 'mail.channel';
            }
            if ('create_uid' in data) {
                data2.creator = insert({ id: data.create_uid });
            }
            if ('custom_channel_name' in data) {
                data2.custom_channel_name = data.custom_channel_name;
            }
            if ('group_based_subscription' in data) {
                data2.group_based_subscription = data.group_based_subscription;
            }
            if ('guestMembers' in data) {
                data2.guestMembers = data.guestMembers;
            }
            if ('id' in data) {
                data2.id = data.id;
            }
            if ('invitedGuests' in data) {
                data2.invitedGuests = data.invitedGuests;
            }
            if ('invitedPartners' in data) {
                data2.invitedPartners = data.invitedPartners;
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
            if ('memberCount' in data) {
                data2.memberCount = data.memberCount;
            }
            if ('message_needaction_counter' in data) {
                data2.message_needaction_counter = data.message_needaction_counter;
            }
            if ('message_unread_counter' in data) {
                data2.serverMessageUnreadCounter = data.message_unread_counter;
            }
            if ('name' in data) {
                data2.name = data.name;
            }
            if ('public' in data) {
                data2.public = data.public;
            }
            if ('seen_message_id' in data) {
                data2.lastSeenByCurrentPartnerMessageId = data.seen_message_id || 0;
            }
            if ('uuid' in data) {
                data2.uuid = data.uuid;
            }

            // relations
            if ('members' in data) {
                // The list syntax is kept here because it is used in livechat override
                if (!data.members) {
                    data2.members = [clear()];
                } else {
                    data2.members = [insertAndReplace(data.members.map(memberData =>
                        this.messaging.models['Partner'].convertData(memberData)
                    ))];
                }
            }
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
                    data2.partnerSeenInfos = insertAndReplace(
                        data.seen_partners_info.map(
                            ({ fetched_message_id, partner_id, seen_message_id }) => {
                                return {
                                    lastFetchedMessage: fetched_message_id ? insert({ id: fetched_message_id }) : clear(),
                                    lastSeenMessage: seen_message_id ? insert({ id: seen_message_id }) : clear(),
                                    partner: insertAndReplace({ id: partner_id }),
                            };
                        })
                    );
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
                            data2.messageSeenIndicators = insertAndReplace([...messageIds].map(messageId => {
                                return {
                                    message: insertAndReplace({ id: messageId }),
                                };
                            }));
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
                Object.assign(
                    { model: 'mail.channel' },
                    this.messaging.models['Thread'].convertData(channelData),
                )
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
                const isAPublic = a.model === 'mail.channel' && a.public === 'public';
                const isBPublic = b.model === 'mail.channel' && b.public === 'public';
                if (isAPublic && !isBPublic) {
                    return -1;
                }
                if (!isAPublic && isBPublic) {
                    return 1;
                }
                const isMemberOfA = a.model === 'mail.channel' && a.members.includes(this.messaging.currentPartner);
                const isMemberOfB = b.model === 'mail.channel' && b.members.includes(this.messaging.currentPartner);
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
         * @param {string} [param0.privacy]
         * @returns {Thread} the created channel
         */
        async performRpcCreateChannel({ name, privacy }) {
            const data = await this.messaging.rpc({
                model: 'mail.channel',
                method: 'channel_create',
                args: [name, privacy],
            });
            return this.messaging.models['Thread'].insert(
                this.messaging.models['Thread'].convertData(data)
            );
        },
        /**
         * Performs the `channel_get` RPC on `mail.channel`.
         *
         * `openChat` is preferable in business code because it will avoid the
         * RPC if the chat already exists.
         *
         * @param {Object} param0
         * @param {integer[]} param0.partnerIds
         * @param {boolean} [param0.pinForCurrentPartner]
         * @returns {Thread|undefined} the created or existing chat
         */
        async performRpcCreateChat({ partnerIds, pinForCurrentPartner }) {
            // TODO FIX: potential duplicate chat task-2276490
            const data = await this.messaging.rpc({
                model: 'mail.channel',
                method: 'channel_get',
                kwargs: {
                    partners_to: partnerIds,
                    pin: pinForCurrentPartner,
                },
            });
            if (!data) {
                return;
            }
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
            return this.insert(channelsData.map(
                channelData => this.convertData(channelData)
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
            if (thread && thread.model === 'mail.channel' && thread.public !== 'public') {
                // Only return the current channel when in the context of a
                // non-public channel. Indeed, the message with the mention
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
                thread.model === 'mail.channel' &&
                thread.channel_type === 'channel' &&
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
                followers: followersData,
                hasWriteAccess,
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
            const values = { hasWriteAccess };
            if (activitiesData) {
                Object.assign(values, {
                    activities: insertAndReplace(activitiesData.map(activityData =>
                        this.messaging.models['Activity'].convertData(activityData)
                    )),
                });
            }
            if (attachmentsData) {
                Object.assign(values, {
                    areAttachmentsLoaded: true,
                    isLoadingAttachments: false,
                    originThreadAttachments: insertAndReplace(attachmentsData),
                });
            }
            if (followersData) {
                Object.assign(values, {
                    followers: insertAndReplace(followersData.map(followerData =>
                        this.messaging.models['Follower'].convertData(followerData)
                    )),
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
                    suggestedRecipientInfoList: insertAndReplace(recipientInfoList),
                });
            }
            this.update(values);
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
            if (!this.messaging.rtc.isClientRtcCompatible) {
                this.messaging.notify({
                    message: this.env._t("Your browser does not support webRTC."),
                    type: 'warning',
                });
                return;
            }
            const { rtcSessions, iceServers, sessionId, invitedPartners, invitedGuests } = await this.messaging.rpc({
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
                rtc: replace(this.messaging.rtc),
                rtcInvitingSession: clear(),
                rtcSessions,
                invitedGuests,
                invitedPartners,
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
         * Returns the name of the given partner in the context of this thread.
         *
         * @param {mail.partner} partner
         * @returns {string}
         */
        getMemberName(partner) {
            return partner.nameOrDisplayName;
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
            if (this.channel_type === 'channel') {
                await this.leave();
                return;
            }
            await this.messaging.models['Thread'].performRpcChannelPin({
                channelId: this.id,
                pinned: this.isPendingPinned,
            });
        },
        /**
         * Handles click on the avatar of the given member in the member list of
         * this channel.
         *
         * @param {Partner} member
         */
        onClickMemberAvatar(member) {
            member.openChat();
        },
        /**
         * Handles click on the name of the given member in the member list of
         * this channel.
         *
         * @param {Partner} member
         */
        onClickMemberName(member) {
            member.openProfile();
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
            if (!['mail.box', 'mail.channel'].includes(this.model)) {
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
                this.model === 'mail.box'
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
            this.update({ currentPartnerInactiveTypingTimer: [clear(), insertAndReplace()] });
        },
        /**
         * Called to refresh a registered other member partner that is typing
         * something.
         *
         * @param {Partner} partner
         */
        refreshOtherMemberTypingMember(partner) {
            this.update({
                otherMembersLongTypingTimers: [
                    insertAndUnlink({ partner: replace(partner) }),
                    insert({ partner: replace(partner) }),
                ],
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
                currentPartnerInactiveTypingTimer: insertAndReplace(),
                currentPartnerLongTypingTimer: insertAndReplace(),
            });
            // Manage typing member relation.
            const currentPartner = this.messaging.currentPartner;
            const newOrderedTypingMembers = [
                ...this.orderedTypingMembers.filter(member => member !== currentPartner),
                currentPartner,
            ];
            this.update({
                isCurrentPartnerTyping: true,
                orderedTypingMembers: replace(newOrderedTypingMembers),
                typingMembers: link(currentPartner),
            });
            // Notify typing status to other members.
            await this.throttleNotifyCurrentPartnerTypingStatus.do();
        },
        /**
         * Called to register a new other member partner that is typing
         * something.
         *
         * @param {Partner} partner
         */
        registerOtherMemberTypingMember(partner) {
            this.update({ otherMembersLongTypingTimers: insert({ partner: replace(partner) }) });
            const newOrderedTypingMembers = [
                ...this.orderedTypingMembers.filter(member => member !== partner),
                partner,
            ];
            this.update({
                orderedTypingMembers: replace(newOrderedTypingMembers),
                typingMembers: link(partner),
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
            const currentPartner = this.messaging.currentPartner;
            const newOrderedTypingMembers = this.orderedTypingMembers.filter(member => member !== currentPartner);
            this.update({
                isCurrentPartnerTyping: false,
                orderedTypingMembers: replace(newOrderedTypingMembers),
                typingMembers: unlink(currentPartner),
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
         * @param {Partner} partner
         */
        unregisterOtherMemberTypingMember(partner) {
            this.update({ otherMembersLongTypingTimers: insertAndUnlink({ partner: replace(partner) }) });
            const newOrderedTypingMembers = this.orderedTypingMembers.filter(member => member !== partner);
            this.update({
                orderedTypingMembers: replace(newOrderedTypingMembers),
                typingMembers: unlink(partner),
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
         * @returns {Attachment[]}
         */
        _computeAllAttachments() {
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
            return replace(allAttachments);
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeComposer() {
            if (this.model === 'mail.box') {
                return clear();
            }
            return insertAndReplace();
        },
        /**
         * @private
         * @returns {Partner}
         */
        _computeCorrespondent() {
            if (this.channel_type === 'channel') {
                return clear();
            }
            const correspondents = this.members.filter(partner =>
                partner !== this.messaging.currentPartner
            );
            if (correspondents.length === 1) {
                // 2 members chat
                return replace(correspondents[0]);
            }
            if (this.members.length === 1) {
                // chat with oneself
                return replace(this.members[0]);
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeCorrespondentOfDmChat() {
            if (
                this.channel_type === 'chat' &&
                this.correspondent &&
                this.model === 'mail.channel' &&
                this.public === 'private'
            ) {
                return replace(this.correspondent);
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeDiscussSidebarCategoryItem() {
            if (this.model !== 'mail.channel') {
                return clear();
            }
            if (!this.isPinned) {
                return clear();
            }
            if (!this.messaging.discuss) {
                return clear();
            }
            const discussSidebarCategory = this._getDiscussSidebarCategory();
            if (!discussSidebarCategory) {
                return clear();
            }
            return insertAndReplace({ category: replace(discussSidebarCategory) });
        },
        /**
         * @private
         * @returns {string}
         */
        _computeDisplayName() {
            if (this.channel_type === 'chat' && this.correspondent) {
                return this.custom_channel_name || this.correspondent.nameOrDisplayName;
            }
            if (this.channel_type === 'group' && !this.name) {
                const partnerNames = this.members.map(partner => partner.nameOrDisplayName);
                const guestNames = this.guestMembers.map(guest => guest.name);
                return [...partnerNames, ...guestNames].join(this.env._t(", "));
            }
            return this.name;
        },
        /**
         * @private
         * @returns {Object}
         */
        _computeFetchMessagesParams() {
            if (this.model === 'mail.box') {
                return {};
            }
            if (this.model === 'mail.channel') {
                return { 'channel_id': this.id };
            }
            return {
                'thread_id': this.id,
                'thread_model': this.model,
            };
        },
        /**
         * @private
         * @returns {string}
         */
        _computeFetchMessagesUrl() {
            switch (this) {
                case this.messaging.inbox:
                    return '/mail/inbox/messages';
                case this.messaging.history:
                    return '/mail/history/messages';
                case this.messaging.starred:
                    return '/mail/starred/messages';
            }
            if (this.model === 'mail.channel') {
                return `/mail/channel/messages`;
            }
            return `/mail/thread/messages`;
        },
        /**
         * @private
         * @returns {Activity[]}
         */
        _computeFutureActivities() {
            return replace(this.activities.filter(activity => activity.state === 'planned'));
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasCallFeature() {
            return ['channel', 'chat', 'group'].includes(this.channel_type);
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasInviteFeature() {
            return this.model === 'mail.channel';
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasSeenIndicators() {
            if (this.model !== 'mail.channel') {
                return false;
            }
            return ['chat', 'livechat'].includes(this.channel_type);
        },
        /**
        * @private
        * @returns {boolean}
        */
        _computeIsChannelDescriptionChangeable() {
            return this.model === 'mail.channel' && ['channel', 'group'].includes(this.channel_type);
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsDescriptionEditableByCurrentUser() {
            return Boolean(
                this.messaging.currentUser &&
                this.messaging.currentUser.isInternalUser &&
                this.isChannelDescriptionChangeable
            );
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsChannelRenamable() {
            return (
                this.model === 'mail.channel' &&
                ['chat', 'channel', 'group'].includes(this.channel_type)
            );
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasMemberListFeature() {
            return this.model === 'mail.channel' && ['channel', 'group'].includes(this.channel_type);
        },
        /**
         * @returns {string}
         */
        _computeInvitationLink() {
            if (!this.uuid || !this.channel_type || this.channel_type === 'chat') {
                return clear();
            }
            return `${window.location.origin}/chat/${this.id}/${this.uuid}`;
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsChatChannel() {
            return this.channel_type === 'chat' || this.channel_type === 'group';
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsCurrentPartnerFollowing() {
            return this.followers.some(follower =>
                follower.partner && follower.partner === this.messaging.currentPartner
            );
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsPinned() {
            return this.isPendingPinned !== undefined ? this.isPendingPinned : this.isServerPinned;
        },
        /**
         * @private
         * @returns {Message}
         */
        _computeLastCurrentPartnerMessageSeenByEveryone() {
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
            return replace(currentPartnerOrderedSeenMessages.slice().pop());
        },
        /**
         * @private
         * @returns {Message|undefined}
         */
        _computeLastMessage() {
            const {
                length: l,
                [l - 1]: lastMessage,
            } = this.orderedMessages;
            if (lastMessage) {
                return replace(lastMessage);
            }
            return clear();
        },
        /**
         * @private
         * @returns {Message|undefined}
         */
        _computeLastNonTransientMessage() {
            const {
                length: l,
                [l - 1]: lastMessage,
            } = this.orderedNonTransientMessages;
            if (lastMessage) {
                return replace(lastMessage);
            }
            return clear();
        },
        /**
         * Adjusts the last seen message received from the server to consider
         * the following messages also as read if they are either transient
         * messages or messages from the current partner.
         *
         * @private
         * @returns {integer}
         */
        _computeLastSeenByCurrentPartnerMessageId() {
            const firstMessage = this.orderedMessages[0];
            if (
                firstMessage &&
                this.lastSeenByCurrentPartnerMessageId &&
                this.lastSeenByCurrentPartnerMessageId < firstMessage.id
            ) {
                // no deduction can be made if there is a gap
                return this.lastSeenByCurrentPartnerMessageId;
            }
            let lastSeenByCurrentPartnerMessageId = this.lastSeenByCurrentPartnerMessageId;
            for (const message of this.orderedMessages) {
                if (message.id <= this.lastSeenByCurrentPartnerMessageId) {
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
        /**
         * @private
         * @returns {Message|undefined}
         */
        _computeLastNeedactionMessageAsOriginThread() {
            const orderedNeedactionMessagesAsOriginThread = this.needactionMessagesAsOriginThread.sort(
                (m1, m2) => m1.id < m2.id ? -1 : 1
            );
            const {
                length: l,
                [l - 1]: lastNeedactionMessageAsOriginThread,
            } = orderedNeedactionMessagesAsOriginThread;
            if (lastNeedactionMessageAsOriginThread) {
                return replace(lastNeedactionMessageAsOriginThread);
            }
            return clear();
        },
        /**
         * @private
         * @returns {integer}
         */
        _computeLocalMessageUnreadCounter() {
            if (this.model !== 'mail.channel') {
                // unread counter only makes sense on channels
                return clear();
            }
            // By default trust the server up to the last message it used
            // because it's not possible to do better.
            let baseCounter = this.serverMessageUnreadCounter;
            let countFromId = this.serverLastMessage ? this.serverLastMessage.id : 0;
            // But if the client knows the last seen message that the server
            // returned (and by assumption all the messages that come after),
            // the counter can be computed fully locally, ignoring potentially
            // obsolete values from the server.
            const firstMessage = this.orderedMessages[0];
            if (
                firstMessage &&
                this.lastSeenByCurrentPartnerMessageId &&
                this.lastSeenByCurrentPartnerMessageId >= firstMessage.id
            ) {
                baseCounter = 0;
                countFromId = this.lastSeenByCurrentPartnerMessageId;
            }
            // Include all the messages that are known locally but the server
            // didn't take into account.
            return this.orderedMessages.reduce((total, message) => {
                if (message.id <= countFromId) {
                    return total;
                }
                return total + 1;
            }, baseCounter);
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMessagingAsRingingThread() {
            if (this.rtcInvitingSession) {
                return replace(this.messaging);
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMessagingMenuAsPinnedAndUnreadChannel() {
            if (!this.messaging.messagingMenu) {
                return clear();
            }
            return (this.model === 'mail.channel' && this.isPinned && this.localMessageUnreadCounter > 0)
                ? replace(this.messaging.messagingMenu)
                : clear();
        },
        /**
         * @private
         * @returns {Message[]}
         */
        _computeNeedactionMessagesAsOriginThread() {
            return replace(this.messagesAsOriginThread.filter(message => message.isNeedaction));
        },
        /**
         * @private
         * @returns {Message|undefined}
         */
        _computeMessageAfterNewMessageSeparator() {
            if (this.model !== 'mail.channel') {
                return clear();
            }
            if (this.localMessageUnreadCounter === 0) {
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
            return replace(message);
        },
        /**
         * @private
         * @returns {Partner[]}
         */
        _computeOrderedOfflineMembers() {
            return replace(this._sortMembers(this.members.filter(member => !member.isOnline)));
        },
        /**
         * @private
         * @returns {Partner[]}
         */
        _computeOrderedOnlineMembers() {
            return replace(this._sortMembers(this.members.filter(member => member.isOnline)));
        },
        /**
         * @private
         * @returns {Message[]}
         */
        _computeOrderedMessages() {
            return replace(this.messages.sort((m1, m2) => m1.id < m2.id ? -1 : 1));
        },
        /**
         * @private
         * @returns {Message[]}
         */
        _computeOrderedNonTransientMessages() {
            return replace(this.orderedMessages.filter(m => !m.isTransient));
        },
        /**
         * @private
         * @returns {Partner[]}
         */
        _computeOrderedOtherTypingMembers() {
            return replace(this.orderedTypingMembers.filter(
                member => member !== this.messaging.currentPartner
            ));
        },
        /**
         * @private
         * @returns {Activity[]}
         */
        _computeOverdueActivities() {
            return replace(this.activities.filter(activity => activity.state === 'overdue'));
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeCallInviteRequestPopup() {
            if (this.rtcInvitingSession) {
                return insertAndReplace();
            }
            return clear();
        },
        /**
         * @private
         * @returns {Throttle}
         */
        _computeThrottleNotifyCurrentPartnerTypingStatus() {
            return insertAndReplace({
                func: () => this._notifyCurrentPartnerTypingStatus(),
            });
        },
        /**
         * @private
         * @returns {Activity[]}
         */
        _computeTodayActivities() {
            return replace(this.activities.filter(activity => activity.state === 'today'));
        },
        /**
         * @private
         * @returns {string}
         */
        _computeTypingStatusText() {
            if (this.orderedOtherTypingMembers.length === 0) {
                return clear();
            }
            if (this.orderedOtherTypingMembers.length === 1) {
                return sprintf(
                    this.env._t("%s is typing..."),
                    this.getMemberName(this.orderedOtherTypingMembers[0])
                );
            }
            if (this.orderedOtherTypingMembers.length === 2) {
                return sprintf(
                    this.env._t("%s and %s are typing..."),
                    this.getMemberName(this.orderedOtherTypingMembers[0]),
                    this.getMemberName(this.orderedOtherTypingMembers[1])
                );
            }
            return sprintf(
                this.env._t("%s, %s and more are typing..."),
                this.getMemberName(this.orderedOtherTypingMembers[0]),
                this.getMemberName(this.orderedOtherTypingMembers[1])
            );
        },
        /**
         * @private
         * @returns {integer}
         */
        _computeUnknownMemberCount() {
            return this.memberCount - this.members.length;
        },
        /**
         * Compute an url string that can be used inside a href attribute
         *
         * @private
         * @returns {string}
         */
        _computeUrl() {
            const baseHref = url('/web');
            if (this.model === 'mail.channel') {
                return `${baseHref}#action=mail.action_discuss&active_id=${this.model}_${this.id}`;
            }
            return `${baseHref}#model=${this.model}&id=${this.id}`;
        },
        /**
         * @private
         * @returns {number}
         */
        _computeVideoCount() {
            return this.rtcSessions.filter(session => session.videoStream).length;
        },
        /**
         * Returns the discuss sidebar category that corresponds to this channel
         * type.
         *
         * @private
         * @returns {DiscussSidebarCategory}
         */
        _getDiscussSidebarCategory() {
            switch (this.channel_type) {
                case 'channel':
                    return this.messaging.discuss.categoryChannel;
                case 'chat':
                case 'group':
                    return this.messaging.discuss.categoryChat;
            }
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
                        model: 'mail.channel',
                        method: 'notify_typing',
                        args: [this.id],
                        kwargs: { is_typing: this.isCurrentPartnerTyping },
                    }, { shadow: true });
                    if (!this.exists()) {
                        return;
                    }
                }
                if (this.isCurrentPartnerTyping && this.currentPartnerLongTypingTimer) {
                    this.update({ currentPartnerLongTypingTimer: [clear(), insertAndReplace()] });
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
         * @private
         * @returns {Array[]}
         */
        _sortGuestMembers() {
            return [
                ['defined-first', 'name'],
                ['case-insensitive-asc', 'name'],
            ];
        },
        /**
         * @private
         * @returns {Array[]}
         */
        _sortPartnerMembers() {
            return [
                ['defined-first', 'nameOrDisplayName'],
                ['case-insensitive-asc', 'nameOrDisplayName'],
            ];
        },
        /**
         * @private
         * @param {Partner[]} members
         * @returns {Partner[]}
         */
        _sortMembers(members) {
            return [...members].sort((a, b) => {
                const cleanedAName = cleanSearchTerm(a.nameOrDisplayName || '');
                const cleanedBName = cleanSearchTerm(b.nameOrDisplayName || '');
                if (cleanedAName < cleanedBName) {
                    return -1;
                }
                if (cleanedAName > cleanedBName) {
                    return 1;
                }
                return a.id - b.id;
            });
        },
        /**
         * Event handler for clicking thread in discuss app.
         */
        async onClick() {
            await this.open();
        },
        /**
         * Handles click on the "load more members" button.
         */
        async onClickLoadMoreMembers() {
            const members = await this.messaging.rpc({
                model: 'mail.channel',
                method: 'load_more_members',
                args: [[this.id]],
                kwargs: {
                    'known_member_ids': this.members.map(partner => partner.id),
                },
            });
            this.update({ members });
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
                isCurrentPartnerTyping: true,
                forceNotifyNextCurrentPartnerTypingStatus: true,
            });
            this.throttleNotifyCurrentPartnerTypingStatus.clear();
            await this.throttleNotifyCurrentPartnerTypingStatus.do();
        },
    },
    fields: {
        /**
         * Determines the `mail.activity` that belong to `this`, assuming `this`
         * has activities (@see hasActivities).
         */
        activities: many('Activity', {
            inverse: 'thread',
        }),
        allAttachments: many('Attachment', {
            compute: '_computeAllAttachments',
        }),
        areAttachmentsLoaded: attr({
            default: false,
        }),
        attachments: many('Attachment', {
            inverse: 'threads',
        }),
        authorizedGroupFullName: attr(),
        /**
         * Cache key to force a reload of the avatar when avatar is changed.
         * It only makes sense for channels.
         */
        avatarCacheKey: attr(),
        cache: one('ThreadCache', {
            default: insertAndReplace(),
            inverse: 'thread',
            isCausal: true,
            readonly: true,
            required: true,
        }),
        channel_type: attr(),
        /**
         * States the chat window related to this thread (if any).
         */
        chatWindow: one('ChatWindow', {
            inverse: 'thread',
            isCausal: true,
        }),
        /**
         * Determines the composer state of this thread.
         */
        composer: one('Composer', {
            compute: '_computeComposer',
            inverse: 'thread',
            isCausal: true,
            readonly: true,
        }),
        correspondent: one('Partner', {
            compute: '_computeCorrespondent',
        }),
        correspondentOfDmChat: one('Partner', {
            compute: '_computeCorrespondentOfDmChat',
            inverse: 'dmChatWithCurrentPartner',
        }),
        counter: attr({
            default: 0,
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
            isCausal: true,
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
            isCausal: true,
        }),
        custom_channel_name: attr(),
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
        /**
         * Determines the discuss sidebar category item that displays this
         * thread (if any). Only applies to channels.
         */
        discussSidebarCategoryItem: one('DiscussSidebarCategoryItem', {
            compute: '_computeDiscussSidebarCategoryItem',
            inverse: 'channel',
            isCausal: true,
            readonly: true,
        }),
        displayName: attr({
            compute: '_computeDisplayName',
        }),
        fetchMessagesParams: attr({
            compute: '_computeFetchMessagesParams',
        }),
        fetchMessagesUrl: attr({
            compute: '_computeFetchMessagesUrl',
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
            compute: '_computeFutureActivities',
        }),
        group_based_subscription: attr({
            default: false,
        }),
        guestMembers: many('Guest', {
            sort: '_sortGuestMembers',
        }),
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
            compute: '_computeHasCallFeature',
        }),
        /**
         * States whether this thread should has the invite feature. Only makes
         * sense for channels.
         */
        hasInviteFeature: attr({
            compute: '_computeHasInviteFeature',
        }),
        /**
         * Determines whether it makes sense for this thread to have a member list.
         */
        hasMemberListFeature: attr({
            compute: '_computeHasMemberListFeature',
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
            compute: '_computeHasSeenIndicators',
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
            readonly: true,
            required: true,
        }),
        invitationLink: attr({
            compute: '_computeInvitationLink',
        }),
        /**
         * List of guests that have been invited to the RTC call of this channel.
         * FIXME should be simplified if we have the mail.channel.partner model
         * in which case the two following fields should be a single relation to that model.
         */
        invitedGuests: many('Guest'),
        /**
         * List of partners that have been invited to the RTC call of this channel.
         */
        invitedPartners: many('Partner'),
        /**
         * Determines whether this description can be changed.
         * Only makes sense for channels.
         */
        isChannelDescriptionChangeable: attr({
            compute: '_computeIsChannelDescriptionChangeable',
        }),
        /**
         * Determines whether this thread can be renamed.
         * Only makes sense for channels.
         */
        isChannelRenamable: attr({
            compute: '_computeIsChannelRenamable',
        }),
        /**
         * States whether this thread is a `mail.channel` qualified as chat.
         *
         * Useful to list chat channels, like in messaging menu with the filter
         * 'chat'.
         */
        isChatChannel: attr({
            compute: '_computeIsChatChannel',
            default: false,
        }),
        isCurrentPartnerFollowing: attr({
            compute: '_computeIsCurrentPartnerFollowing',
            default: false,
        }),
        isCurrentPartnerTyping: attr({
            default: false,
        }),
        /**
         * States whether this thread description is editable by the current user.
         */
        isDescriptionEditableByCurrentUser: attr({
            compute: '_computeIsDescriptionEditableByCurrentUser',
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
            compute: '_computeIsPinned',
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
            compute: '_computeLastCurrentPartnerMessageSeenByEveryone',
        }),
        /**
         * Last message of the thread, could be a transient one.
         */
        lastMessage: one('Message', {
            compute: '_computeLastMessage',
        }),
        /**
         * States the last known needaction message having this thread as origin.
         */
        lastNeedactionMessageAsOriginThread: one('Message', {
            compute: '_computeLastNeedactionMessageAsOriginThread',
        }),
        /**
         * Last non-transient message.
         */
        lastNonTransientMessage: one('Message', {
            compute: '_computeLastNonTransientMessage',
        }),
        /**
         * Last seen message id of the channel by current partner.
         *
         * Also, it needs to be kept as an id because it's considered like a "date" and could stay
         * even if corresponding message is deleted. It is basically used to know which
         * messages are before or after it.
         */
        lastSeenByCurrentPartnerMessageId: attr({
            compute: '_computeLastSeenByCurrentPartnerMessageId',
            default: 0,
        }),
        /**
         * Local value of message unread counter, that means it is based on initial server value and
         * updated with interface updates.
         */
        localMessageUnreadCounter: attr({
            compute: '_computeLocalMessageUnreadCounter',
        }),
        /**
         * States the number of members in this thread according to the server.
         * Guests are excluded from the count.
         * Only makes sense if this thread is a channel.
         */
        memberCount: attr(),
        members: many('Partner', {
            inverse: 'memberThreads',
            sort: '_sortPartnerMembers',
        }),
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
            compute: '_computeMessageAfterNewMessageSeparator',
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
            isCausal: true,
        }),
        messagingAsRingingThread: one('Messaging', {
            compute: '_computeMessagingAsRingingThread',
            inverse: 'ringingThreads',
            readonly: true,
        }),
        messagingMenuAsPinnedAndUnreadChannel: one('MessagingMenu', {
            compute: '_computeMessagingMenuAsPinnedAndUnreadChannel',
            inverse: 'pinnedAndUnreadChannels',
            readonly: true,
        }),
        model: attr({
            readonly: true,
            required: true,
        }),
        model_name: attr(),
        moduleIcon: attr(),
        name: attr(),
        /**
         * States all known needaction messages having this thread as origin.
         */
        needactionMessagesAsOriginThread: many('Message', {
            compute: '_computeNeedactionMessagesAsOriginThread',
        }),
        /**
         * All offline members ordered like they are displayed.
         */
        orderedOfflineMembers: many('Partner', {
            compute: '_computeOrderedOfflineMembers',
        }),
        /**
         * All online members ordered like they are displayed.
         */
        orderedOnlineMembers: many('Partner', {
            compute: '_computeOrderedOnlineMembers',
        }),
        /**
         * All messages ordered like they are displayed.
         */
        orderedMessages: many('Message', {
            compute: '_computeOrderedMessages',
        }),
        /**
         * All messages ordered like they are displayed. This field does not
         * contain transient messages which are not "real" records.
         */
        orderedNonTransientMessages: many('Message', {
            compute: '_computeOrderedNonTransientMessages',
        }),
        /**
         * Ordered typing members on this thread, excluding the current partner.
         */
        orderedOtherTypingMembers: many('Partner', {
            compute: '_computeOrderedOtherTypingMembers',
        }),
        /**
         * Ordered list of typing members.
         */
        orderedTypingMembers: many('Partner'),
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
            isCausal: true,
        }),
        /**
         * States the `Activity` that belongs to `this` and that are
         * overdue (due earlier than today).
         */
        overdueActivities: many('Activity', {
            compute: '_computeOverdueActivities',
        }),
        /**
         * Contains the seen information for all members of the thread.
         * FIXME This field should be readonly once task-2336946 is done.
         */
        partnerSeenInfos: many('ThreadPartnerSeenInfo', {
            inverse: 'thread',
            isCausal: true,
        }),
        /**
         * Determine if there is a pending seen message change, which is a change
         * of seen message requested by the client but not yet confirmed by the
         * server.
         */
        pendingSeenMessageId: attr(),
        public: attr(),
        /**
         * If set, the current thread is the thread that hosts the current RTC call.
         */
        rtc: one('Rtc', {
            inverse: 'channel',
        }),
        callInviteRequestPopup: one('CallInviteRequestPopup', {
            compute: '_computeCallInviteRequestPopup',
            inverse: 'thread',
            isCausal: true,
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
        /**
         * Message unread counter coming from server.
         *
         * Value of this field is unreliable, due to dynamic nature of
         * messaging. So likely outdated/unsync with server. Should use
         * localMessageUnreadCounter instead, which smartly guess the actual
         * message unread counter at all time.
         *
         * @see localMessageUnreadCounter
         */
        serverMessageUnreadCounter: attr({
            default: 0,
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
            compute: '_computeThrottleNotifyCurrentPartnerTypingStatus',
            inverse: 'threadAsThrottleNotifyCurrentPartnerTypingStatus',
            isCausal: true,
        }),
        /**
         * States the `Activity` that belongs to `this` and that are due
         * specifically today.
         */
        todayActivities: many('Activity', {
            compute: '_computeTodayActivities',
        }),
        threadNeedactionPreviewViews: many('ThreadNeedactionPreviewView', {
            inverse: 'thread',
            isCausal: true,
        }),
        threadPreviewViews: many('ThreadPreviewView', {
            inverse: 'thread',
            isCausal: true,
        }),
        /**
         * Members that are currently typing something in the composer of this
         * thread, including current partner.
         */
        typingMembers: many('Partner'),
        /**
         * Text that represents the status on this thread about typing members.
         */
        typingStatusText: attr({
            compute: '_computeTypingStatusText',
            default: '',
        }),
        /**
         * States how many members are currently unknown on the client side.
         * This is the difference between the total number of members of the
         * channel as reported in memberCount and those actually in members.
         */
        unknownMemberCount: attr({
            compute: '_computeUnknownMemberCount',
        }),
        /**
         * URL to access to the conversation.
         */
        url: attr({
            compute: '_computeUrl',
            default: '',
        }),
        uuid: attr(),
        /**
         * The amount of videos broadcast in the current Rtc call
         */
        videoCount: attr({
            compute: '_computeVideoCount',
            default: 0,
        }),
    },
    onChanges: [
        new OnChange({
            dependencies: ['lastSeenByCurrentPartnerMessageId'],
            methodName: '_onChangeLastSeenByCurrentPartnerMessageId',
        }),
        new OnChange({
            dependencies: ['isServerPinned'],
            methodName: '_onIsServerPinnedChanged',
        }),
        new OnChange({
            dependencies: ['serverFoldState'],
            methodName: '_onServerFoldStateChanged',
        }),
    ],
});
