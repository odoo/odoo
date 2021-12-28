/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2many, many2one, one2many, one2one } from '@mail/model/model_field';
import { clear, insert, insertAndReplace, link, replace, unlink, unlinkAll } from '@mail/model/model_field_command';
import { OnChange } from '@mail/model/model_onchange';
import throttle from '@mail/utils/throttle/throttle';
import Timer from '@mail/utils/timer/timer';
import { cleanSearchTerm } from '@mail/utils/utils';
import * as mailUtils from '@mail/js/utils';

import { str_to_datetime } from 'web.time';

function factory(dependencies) {

    const getSuggestedRecipientInfoNextTemporaryId = (function () {
        let tmpId = 0;
        return () => {
            tmpId += 1;
            return tmpId;
        };
    })();

    class Thread extends dependencies['mail.model'] {

        /**
         * @override
         */
        _willCreate() {
            const res = super._willCreate(...arguments);
            /**
             * Timer of current partner that was currently typing something, but
             * there is no change on the input for 5 seconds. This is used
             * in order to automatically notify other members that current
             * partner has stopped typing something, due to making no changes
             * on the composer for some time.
             */
            this._currentPartnerInactiveTypingTimer = new Timer(
                this.env,
                () => this.async(() => {
                    if (this.messaging.currentPartner) {
                        return this._onCurrentPartnerInactiveTypingTimeout();
                    }
                }),
                5 * 1000
            );
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
            this._currentPartnerLastNotifiedIsTyping = undefined;
            /**
             * Timer of current partner that is typing a very long text. When
             * the other members do not receive any typing notification for a
             * long time, they must assume that the related partner is no longer
             * typing something (e.g. they have closed the browser tab).
             * This is a timer to let other members know that current partner
             * is still typing something, so that they should not assume he/she
             * has stopped typing something.
             */
            this._currentPartnerLongTypingTimer = new Timer(
                this.env,
                () => this.async(() => this._onCurrentPartnerLongTypingTimeout()),
                50 * 1000
            );
            /**
             * Determines whether the next request to notify current partner
             * typing status should always result to making RPC, regardless of
             * whether last notified current partner typing status is the same.
             * Most of the time we do not want to notify if value hasn't
             * changed, exception being the long typing scenario of current
             * partner.
             */
            this._forceNotifyNextCurrentPartnerTypingStatus = false;
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
            this._otherMembersLongTypingTimers = new Map();

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
            this._throttleNotifyCurrentPartnerTypingStatus = throttle(
                this.env,
                ({ isTyping }) => this.async(() => this._notifyCurrentPartnerTypingStatus({ isTyping })),
                2.5 * 1000
            );
            return res;
        }

        /**
         * @override
         */
        _created() {
            super._created();
            this.onClick = this.onClick.bind(this);
            this.onClickLoadMoreMembers = this.onClickLoadMoreMembers.bind(this);
        }

        /**
         * @override
         */
        _willDelete() {
            this._currentPartnerInactiveTypingTimer.clear();
            this._currentPartnerLongTypingTimer.clear();
            this._throttleNotifyCurrentPartnerTypingStatus.clear();
            for (const timer of this._otherMembersLongTypingTimers.values()) {
                timer.clear();
            }
            if (this.isTemporary) {
                for (const message of this.messages) {
                    message.delete();
                }
            }
            return super._willDelete(...arguments);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Changes description of the thread to the given new description.
         * Only makes sense for channels.
         *
         * @param {string} description
         */
        async changeDescription(description) {
            this.update({ description });
            return this.env.services.rpc({
                model: 'mail.channel',
                method: 'channel_change_description',
                args: [[this.id]],
                kwargs: { description },
            });
        }

        /**
         * @static
         * @param {mail.thread} [thread] the concerned thread
         */
        static computeLastCurrentPartnerMessageSeenByEveryone(thread = undefined) {
            const threads = thread ? [thread] : this.messaging.models['mail.thread'].all();
            threads.map(localThread => {
                localThread.update({
                    lastCurrentPartnerMessageSeenByEveryone: localThread._computeLastCurrentPartnerMessageSeenByEveryone(),
                });
            });
        }

        /**
         * @static
         * @param {Object} data
         * @return {Object}
         */
        static convertData(data) {
            const data2 = {};
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
                const messageData = this.messaging.models['mail.message'].convertData({
                    id: data.last_message.id,
                    model: data2.model,
                    res_id: data2.id,
                });
                data2.serverLastMessage = insert(messageData);
            }
            if ('last_message_id' in data && data.last_message_id) {
                const messageData = this.messaging.models['mail.message'].convertData({
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
                    data2.members = [unlinkAll()];
                } else {
                    data2.members = [insertAndReplace(data.members.map(memberData =>
                        this.messaging.models['mail.partner'].convertData(memberData)
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
                    data2.partnerSeenInfos = unlinkAll();
                } else {
                    data2.partnerSeenInfos = insertAndReplace(
                        data.seen_partners_info.map(
                            ({ fetched_message_id, partner_id, seen_message_id }) => {
                                return {
                                    lastFetchedMessage: fetched_message_id ? insert({ id: fetched_message_id }) : unlinkAll(),
                                    lastSeenMessage: seen_message_id ? insert({ id: seen_message_id }) : unlinkAll(),
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
        }

        /**
         * Creates a new group chat with the provided partners.
         *
         * @param {Object} param0
         * @param {number[]} param0.partners_to Ids of the partners to add as channel
         * members.
         * @param {boolean|string} param0.default_display_mode
         * @returns {mail.thread} The newly created group chat.
         */
        static async createGroupChat({ default_display_mode, partners_to }) {
            const channelData = await this.env.services.rpc({
                model: 'mail.channel',
                method: 'create_group',
                kwargs: {
                    default_display_mode,
                    partners_to,
                },
            });
            return this.messaging.models['mail.thread'].insert(
                this.messaging.models['mail.thread'].convertData(channelData)
            );
        }

        /**
         * Client-side ending of the call.
         */
        endCall() {
            if (this.rtc) {
                this.rtc.reset();
                this.messaging.soundEffects.channelLeave.play();
            }
            this.update({
                rtc: unlink(),
                rtcInvitingSession: unlink(),
            });
        }

        /**
         * Fetches threads matching the given composer search state to extend
         * the JS knowledge and to update the suggestion list accordingly.
         * More specifically only thread of model 'mail.channel' are fetched.
         *
         * @static
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {mail.thread} [options.thread] prioritize and/or restrict
         *  result in the context of given thread
         */
        static async fetchSuggestions(searchTerm, { thread } = {}) {
            const channelsData = await this.env.services.rpc(
                {
                    model: 'mail.channel',
                    method: 'get_mention_suggestions',
                    kwargs: { search: searchTerm },
                },
                { shadow: true },
            );
            this.messaging.models['mail.thread'].insert(channelsData.map(channelData =>
                Object.assign(
                    { model: 'mail.channel' },
                    this.messaging.models['mail.thread'].convertData(channelData),
                )
            ));
        }

        /**
         * Returns a sort function to determine the order of display of threads
         * in the suggestion list.
         *
         * @static
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {mail.thread} [options.thread] prioritize result in the
         *  context of given thread
         * @returns {function}
         */
        static getSuggestionSortFunction(searchTerm, { thread } = {}) {
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
        }

        /**
         * Load the previews of the specified threads. Basically, it fetches the
         * last messages, since they are used to display inline content of them.
         *
         * @static
         * @param {mail.thread[]} threads
         */
        static async loadPreviews(threads) {
            const channelIds = threads.reduce((list, thread) => {
                if (thread.model === 'mail.channel') {
                    return list.concat(thread.id);
                }
                return list;
            }, []);
            if (channelIds.length === 0) {
                return;
            }
            const channelPreviews = await this.env.services.rpc({
                model: 'mail.channel',
                method: 'channel_fetch_preview',
                args: [channelIds],
            }, { shadow: true });
            this.messaging.models['mail.message'].insert(channelPreviews.filter(p => p.last_message).map(
                channelPreview => this.messaging.models['mail.message'].convertData(channelPreview.last_message)
            ));
        }

        /**
         * Performs the `channel_fold` RPC on `mail.channel`.
         *
         * @static
         * @param {string} uuid
         * @param {string} state
         */
        static async performRpcChannelFold(uuid, state) {
            return this.env.services.rpc({
                model: 'mail.channel',
                method: 'channel_fold',
                kwargs: {
                    state,
                    uuid,
                }
            }, { shadow: true });
        }

        /**
         * Performs the `channel_info` RPC on `mail.channel`.
         *
         * @static
         * @param {Object} param0
         * @param {integer[]} param0.ids list of id of channels
         * @returns {mail.thread[]}
         */
        static async performRpcChannelInfo({ ids }) {
            const channelInfos = await this.env.services.rpc({
                model: 'mail.channel',
                method: 'channel_info',
                args: [ids],
            }, { shadow: true });
            const channels = this.messaging.models['mail.thread'].insert(
                channelInfos.map(channelInfo => this.messaging.models['mail.thread'].convertData(channelInfo))
            );
            return channels;
        }

        /**
         * Performs the `/mail/channel/set_last_seen_message` RPC.
         *
         * @static
         * @param {Object} param0
         * @param {integer} param0.id id of channel
         * @param {integer[]} param0.lastMessageId
         */
        static async performRpcChannelSeen({ id, lastMessageId }) {
            return this.env.services.rpc({
                route: `/mail/channel/set_last_seen_message`,
                params: {
                    channel_id: id,
                    last_message_id: lastMessageId,
                },
            }, { shadow: true });
        }

        /**
         * Performs the `channel_pin` RPC on `mail.channel`.
         *
         * @static
         * @param {Object} param0
         * @param {boolean} [param0.pinned=false]
         * @param {string} param0.uuid
         */
        static async performRpcChannelPin({ pinned = false, uuid }) {
            return this.env.services.rpc({
                model: 'mail.channel',
                method: 'channel_pin',
                kwargs: {
                    uuid,
                    pinned,
                },
            }, { shadow: true });
        }

        /**
         * Performs the `channel_create` RPC on `mail.channel`.
         *
         * @static
         * @param {Object} param0
         * @param {string} param0.name
         * @param {string} [param0.privacy]
         * @returns {mail.thread} the created channel
         */
        static async performRpcCreateChannel({ name, privacy }) {
            const device = this.messaging.device;
            const data = await this.env.services.rpc({
                model: 'mail.channel',
                method: 'channel_create',
                args: [name, privacy],
                kwargs: {
                    context: Object.assign({}, this.env.session.user_content, {
                        // optimize the return value by avoiding useless queries
                        // in non-mobile devices
                        isMobile: device.isMobile,
                    }),
                },
            });
            return this.messaging.models['mail.thread'].insert(
                this.messaging.models['mail.thread'].convertData(data)
            );
        }

        /**
         * Performs the `channel_get` RPC on `mail.channel`.
         *
         * `openChat` is preferable in business code because it will avoid the
         * RPC if the chat already exists.
         *
         * @static
         * @param {Object} param0
         * @param {integer[]} param0.partnerIds
         * @param {boolean} [param0.pinForCurrentPartner]
         * @returns {mail.thread|undefined} the created or existing chat
         */
        static async performRpcCreateChat({ partnerIds, pinForCurrentPartner }) {
            const device = this.messaging.device;
            // TODO FIX: potential duplicate chat task-2276490
            const data = await this.env.services.rpc({
                model: 'mail.channel',
                method: 'channel_get',
                kwargs: {
                    context: Object.assign({}, this.env.session.user_content, {
                        // optimize the return value by avoiding useless queries
                        // in non-mobile devices
                        isMobile: device.isMobile,
                    }),
                    partners_to: partnerIds,
                    pin: pinForCurrentPartner,
                },
            });
            if (!data) {
                return;
            }
            return this.messaging.models['mail.thread'].insert(
                this.messaging.models['mail.thread'].convertData(data)
            );
        }

        /**
         * Performs the rpc to leave the rtc call of the channel.
         */
        async performRpcLeaveCall() {
            await this.async(() => this.env.services.rpc({
                route: '/mail/rtc/channel/leave_call',
                params: { channel_id: this.id },
            }, { shadow: true }));
        }

        /**
         * Performs RPC on the route `/mail/get_suggested_recipients`.
         *
         * @static
         * @param {Object} param0
         * @param {string} param0.model
         * @param {integer[]} param0.res_id
         */
        static async performRpcMailGetSuggestedRecipients({ model, res_ids }) {
            const data = await this.env.services.rpc({
                route: '/mail/get_suggested_recipients',
                params: {
                    model,
                    res_ids,
                },
            }, { shadow: true });
            for (const id in data) {
                const recipientInfoList = data[id].map(recipientInfoData => {
                    const [partner_id, emailInfo, reason] = recipientInfoData;
                    const [name, email] = emailInfo && mailUtils.parseEmail(emailInfo);
                    return {
                        email,
                        id: getSuggestedRecipientInfoNextTemporaryId(),
                        name,
                        partner: partner_id ? insert({ id: partner_id }) : unlink(),
                        reason,
                    };
                });
                this.insert({
                    id: parseInt(id),
                    model,
                    suggestedRecipientInfoList: insertAndReplace(recipientInfoList),
                });
            }
        }

        /**
         * Search for thread matching `searchTerm`.
         *
         * @static
         * @param {Object} param0
         * @param {integer} param0.limit
         * @param {string} param0.searchTerm
         */
        static async searchChannelsToOpen({ limit, searchTerm }) {
            const domain = [
                ['channel_type', '=', 'channel'],
                ['name', 'ilike', searchTerm],
            ];
            const fields = ['channel_type', 'name'];
            const channelsData = await this.env.services.rpc({
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
        }

        /*
         * Returns threads that match the given search term. More specially only
         * threads of model 'mail.channel' are suggested, and if the context
         * thread is a private channel, only itself is returned if it matches
         * the search term.
         *
         * @static
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {mail.thread} [options.thread] prioritize and/or restrict
         *  result in the context of given thread
         * @returns {[mail.threads[], mail.threads[]]}
         */
        static searchSuggestions(searchTerm, { thread } = {}) {
            let threads;
            if (thread && thread.model === 'mail.channel' && thread.public !== 'public') {
                // Only return the current channel when in the context of a
                // non-public channel. Indeed, the message with the mention
                // would appear in the target channel, so this prevents from
                // inadvertently leaking the private message into the mentioned
                // channel.
                threads = [thread];
            } else {
                threads = this.messaging.models['mail.thread'].all();
            }
            const cleanedSearchTerm = cleanSearchTerm(searchTerm);
            return [threads.filter(thread =>
                !thread.isTemporary &&
                thread.model === 'mail.channel' &&
                thread.channel_type === 'channel' &&
                thread.displayName &&
                cleanSearchTerm(thread.displayName).includes(cleanedSearchTerm)
            )];
        }

        /**
         * Fetch attachments linked to a record. Useful for populating the store
         * with these attachments, which are used by attachment box in the chatter.
         */
        async fetchAttachments() {
            const attachmentsData = await this.async(() => this.env.services.rpc({
                model: 'ir.attachment',
                method: 'search_read',
                domain: [
                    ['res_id', '=', this.id],
                    ['res_model', '=', this.model],
                ],
                fields: ['id', 'name', 'mimetype'],
                orderBy: [{ name: 'id', asc: false }],
            }, { shadow: true }));
            this.update({
                originThreadAttachments: insertAndReplace(attachmentsData),
            });
            this.update({ areAttachmentsLoaded: true });
        }

        /**
         * Fetches suggested recipients.
         */
        async fetchAndUpdateSuggestedRecipients() {
            if (this.isTemporary) {
                return;
            }
            return this.messaging.models['mail.thread'].performRpcMailGetSuggestedRecipients({
                model: this.model,
                res_ids: [this.id],
            });
        }

        /**
         * Add current user to provided thread's followers.
         */
        async follow() {
            await this.async(() => this.env.services.rpc({
                model: this.model,
                method: 'message_subscribe',
                args: [[this.id]],
                kwargs: {
                    partner_ids: [this.messaging.currentPartner.id],
                },
            }));
            this.refreshFollowers();
            this.fetchAndUpdateSuggestedRecipients();
        }

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
        }

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
                this.env.services.notification.notify({
                    message: this.env._t("Your browser does not support webRTC."),
                    type: 'warning',
                });
                return;
            }
            const { rtcSessions, iceServers, sessionId, invitedPartners, invitedGuests } = await this.async(() => this.env.services.rpc({
                route: '/mail/rtc/channel/join_call',
                params: {
                    channel_id: this.id,
                    check_rtc_session_ids: this.rtcSessions.map(rtcSession => rtcSession.id),
                },
            }, { shadow: true }));
            if (!this.exists()) {
                return;
            }
            this.update({
                rtc: link(this.messaging.rtc),
                rtcInvitingSession: unlink(),
                rtcSessions,
                invitedGuests,
                invitedPartners,
            });
            await this.async(() => this.messaging.rtc.initSession({
                currentSessionId: sessionId,
                iceServers,
                startWithAudio: true,
                startWithVideo,
                videoType,
            }));
            this.messaging.soundEffects.channelJoin.play();
        }

        /**
         * Notifies the server and does the cleanup of the current call.
         */
        async leaveCall() {
            await this.performRpcLeaveCall();
            this.endCall();
        }

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
        }

        /**
         * Returns the name of the given partner in the context of this thread.
         *
         * @param {mail.partner} partner
         * @returns {string}
         */
        getMemberName(partner) {
            return partner.nameOrDisplayName;
        }

        /**
         * Returns the text that identifies this thread in a mention.
         *
         * @returns {string}
         */
        getMentionText() {
            return this.name;
        }

        /**
         * Joins this thread. Only makes sense on channels of type channel.
         */
        async join() {
            await this.env.services.rpc({
                model: 'mail.channel',
                method: 'add_members',
                args: [[this.id]],
                kwargs: { partner_ids: [this.messaging.currentPartner.id] }
            });
        }

        /**
         * Leaves this thread. Only makes sense on channels of type channel.
         */
        async leave() {
            await this.env.services.rpc({
                model: 'mail.channel',
                method: 'action_unfollow',
                args: [[this.id]],
            });
        }

        /**
         * Load new messages on the main cache of this thread.
         */
        loadNewMessages() {
            this.cache.loadNewMessages();
        }

        /**
         * Mark the specified conversation as fetched.
         */
        async markAsFetched() {
            await this.async(() => this.env.services.rpc({
                model: 'mail.channel',
                method: 'channel_fetched',
                args: [[this.id]],
            }, { shadow: true }));
        }

        /**
         * Mark the specified conversation as read/seen.
         *
         * @param {mail.message} message the message to be considered as last seen.
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
            return this.messaging.models['mail.thread'].performRpcChannelSeen({
                id: this.id,
                lastMessageId: message.id,
            });
        }

        /**
         * Marks as read all needaction messages with this thread as origin.
         */
        async markNeedactionMessagesAsOriginThreadAsRead() {
            await this.async(() =>
                this.messaging.models['mail.message'].markAsRead(this.needactionMessagesAsOriginThread)
            );
        }

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
            if (!this.uuid) {
                return;
            }
            return this.messaging.models['mail.thread'].performRpcChannelFold(this.uuid, state);
        }

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
            await this.messaging.models['mail.thread'].performRpcChannelPin({
                pinned: this.isPendingPinned,
                uuid: this.uuid,
            });
        }

        /**
         * Handles click on the avatar of the given member in the member list of
         * this channel.
         *
         * @param {mail.partner} member
         */
        onClickMemberAvatar(member) {
            member.openChat();
        }

        /**
         * Handles click on the name of the given member in the member list of
         * this channel.
         *
         * @param {mail.partner} member
         */
        onClickMemberName(member) {
            member.openProfile();
        }

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
                if (expanded || discuss.isOpen) {
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
            const device = this.messaging.device;
            if (
                (!device.isMobile && (discuss.isOpen || expanded)) ||
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
        }

        /**
         * Opens the most appropriate view that is a profile for this thread.
         */
        async openProfile() {
            return this.messaging.openDocument({
                id: this.id,
                model: this.model,
            });
        }

        /**
         * Pin this thread and notify server of the change.
         */
        async pin() {
            this.update({ isPendingPinned: true });
            if (this.messaging.currentGuest) {
                return;
            }
            await this.notifyPinStateToServer();
        }

        /**
         * Open a dialog to add partners as followers.
         */
        promptAddPartnerFollower() {
            this._promptAddFollower();
        }

        async refresh() {
            if (this.isTemporary) {
                return;
            }
            this.loadNewMessages();
            this.update({ isLoadingAttachments: true });
            await this.async(() => this.fetchAttachments());
            this.update({ isLoadingAttachments: false });
        }

        async refreshActivities() {
            if (!this.hasActivities) {
                return;
            }
            if (this.isTemporary) {
                return;
            }
            // A bit "extreme", may be improved
            const [{ activity_ids: newActivityIds }] = await this.async(() => this.env.services.rpc({
                model: this.model,
                method: 'read',
                args: [this.id, ['activity_ids']]
            }, { shadow: true }));
            const activitiesData = await this.async(() => this.env.services.rpc({
                model: 'mail.activity',
                method: 'activity_format',
                args: [newActivityIds]
            }, { shadow: true }));
            const activities = this.messaging.models['mail.activity'].insert(activitiesData.map(
                activityData => this.messaging.models['mail.activity'].convertData(activityData)
            ));
            this.update({ activities: replace(activities) });
        }

        /**
         * Refresh followers information from server.
         */
        async refreshFollowers() {
            if (this.isTemporary) {
                this.update({ followers: unlinkAll() });
                return;
            }
            const { followers } = await this.async(() => this.env.services.rpc({
                route: '/mail/read_followers',
                params: {
                    res_id: this.id,
                    res_model: this.model,
                },
            }, { shadow: true }));
            this.update({ areFollowersLoaded: true });
            if (followers.length > 0) {
                this.update({
                    followers: insertAndReplace(followers.map(data =>
                        this.messaging.models['mail.follower'].convertData(data))
                    ),
                });
            } else {
                this.update({
                    followers: unlinkAll(),
                });
            }
        }

        /**
         * Refresh the typing status of the current partner.
         */
        refreshCurrentPartnerIsTyping() {
            this._currentPartnerInactiveTypingTimer.reset();
        }

        /**
         * Called to refresh a registered other member partner that is typing
         * something.
         *
         * @param {mail.partner} partner
         */
        refreshOtherMemberTypingMember(partner) {
            this._otherMembersLongTypingTimers.get(partner).reset();
        }

        /**
         * Called when current partner is inserting some input in composer.
         * Useful to notify current partner is currently typing something in the
         * composer of this thread to all other members.
         */
        async registerCurrentPartnerIsTyping() {
            // Handling of typing timers.
            this._currentPartnerInactiveTypingTimer.start();
            this._currentPartnerLongTypingTimer.start();
            // Manage typing member relation.
            const currentPartner = this.messaging.currentPartner;
            const newOrderedTypingMemberLocalIds = this.orderedTypingMemberLocalIds
                .filter(localId => localId !== currentPartner.localId);
            newOrderedTypingMemberLocalIds.push(currentPartner.localId);
            this.update({
                orderedTypingMemberLocalIds: newOrderedTypingMemberLocalIds,
                typingMembers: link(currentPartner),
            });
            // Notify typing status to other members.
            await this._throttleNotifyCurrentPartnerTypingStatus({ isTyping: true });
        }

        /**
         * Called to register a new other member partner that is typing
         * something.
         *
         * @param {mail.partner} partner
         */
        registerOtherMemberTypingMember(partner) {
            const timer = new Timer(
                this.env,
                () => this.async(() => this._onOtherMemberLongTypingTimeout(partner)),
                60 * 1000
            );
            this._otherMembersLongTypingTimers.set(partner, timer);
            timer.start();
            const newOrderedTypingMemberLocalIds = this.orderedTypingMemberLocalIds
                .filter(localId => localId !== partner.localId);
            newOrderedTypingMemberLocalIds.push(partner.localId);
            this.update({
                orderedTypingMemberLocalIds: newOrderedTypingMemberLocalIds,
                typingMembers: link(partner),
            });
        }

        /**
         * Renames this thread to the given new name.
         * Only makes sense for channels.
         *
         * @param {string} name
         */
        async rename(name) {
            this.update({ name });
            return this.env.services.rpc({
                model: 'mail.channel',
                method: 'channel_rename',
                args: [[this.id]],
                kwargs: { name },
            });
        }

        /**
         * Sets the custom name of this thread for the current user to the given
         * new name.
         * Only makes sense for channels.
         *
         * @param {string} newName
         */
        async setCustomName(newName) {
            return this.env.services.rpc({
                model: 'mail.channel',
                method: 'channel_set_custom_name',
                args: [this.id],
                kwargs: { name: newName },
            });
        }

        /**
         * Unfollow current partner from this thread.
         */
        async unfollow() {
            const currentPartnerFollower = this.followers.find(
                follower => follower.partner === this.messaging.currentPartner
            );
            await this.async(() => currentPartnerFollower.remove());
        }

        /**
         * Unpin this thread and notify server of the change.
         */
        async unpin() {
            this.update({ isPendingPinned: false });
            if (this.messaging.currentGuest) {
                return;
            }
            await this.notifyPinStateToServer();
        }

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
        async unregisterCurrentPartnerIsTyping({ immediateNotify = false } = {}) {
            // Handling of typing timers.
            this._currentPartnerInactiveTypingTimer.clear();
            this._currentPartnerLongTypingTimer.clear();
            // Manage typing member relation.
            const currentPartner = this.messaging.currentPartner;
            const newOrderedTypingMemberLocalIds = this.orderedTypingMemberLocalIds
                .filter(localId => localId !== currentPartner.localId);
            this.update({
                orderedTypingMemberLocalIds: newOrderedTypingMemberLocalIds,
                typingMembers: unlink(currentPartner),
            });
            // Notify typing status to other members.
            if (immediateNotify) {
                this._throttleNotifyCurrentPartnerTypingStatus.clear();
            }
            await this.async(
                () => this._throttleNotifyCurrentPartnerTypingStatus({ isTyping: false })
            );
        }

        /**
         * Called to unregister an other member partner that is no longer typing
         * something.
         *
         * @param {mail.partner} partner
         */
        unregisterOtherMemberTypingMember(partner) {
            this._otherMembersLongTypingTimers.get(partner).clear();
            this._otherMembersLongTypingTimers.delete(partner);
            const newOrderedTypingMemberLocalIds = this.orderedTypingMemberLocalIds
                .filter(localId => localId !== partner.localId);
            this.update({
                orderedTypingMemberLocalIds: newOrderedTypingMemberLocalIds,
                typingMembers: unlink(partner),
            });
        }

        /**
         * Unsubscribe current user from provided channel.
         */
        unsubscribe() {
            this.leaveCall();
            this.messaging.chatWindowManager.closeThread(this);
            this.unpin();
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {mail.attachment[]}
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
        }

        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeComposer() {
            if (this.model === 'mail.box') {
                return clear();
            }
            return insertAndReplace();
        }

        /**
         * @private
         * @returns {mail.partner}
         */
        _computeCorrespondent() {
            if (this.channel_type === 'channel') {
                return unlink();
            }
            const correspondents = this.members.filter(partner =>
                partner !== this.messaging.currentPartner
            );
            if (correspondents.length === 1) {
                // 2 members chat
                return link(correspondents[0]);
            }
            if (this.members.length === 1) {
                // chat with oneself
                return link(this.members[0]);
            }
            return unlink();
        }

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
            const discussSidebarCategory = this._getDiscussSidebarCategory();
            if (!discussSidebarCategory) {
                return clear();
            }
            return insertAndReplace({ category: replace(discussSidebarCategory) });
        }

        /**
         * @private
         * @returns {string}
         */
        _computeDisplayName() {
            if (this.channel_type === 'chat' && this.correspondent) {
                return this.custom_channel_name || this.correspondent.nameOrDisplayName;
            }
            if (this.channel_type === 'group') {
                return this.name || this.members.map(partner => partner.nameOrDisplayName).join(', ');
            }
            return this.name;
        }

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
        }

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
        }

        /**
         * @private
         * @returns {mail.activity[]}
         */
        _computeFutureActivities() {
            return replace(this.activities.filter(activity => activity.state === 'planned'));
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasInviteFeature() {
            return this.model === 'mail.channel';
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasSeenIndicators() {
            if (this.model !== 'mail.channel') {
                return false;
            }
            return ['chat', 'livechat'].includes(this.channel_type);
        }

        /**
        * @private
        * @returns {boolean}
        */
        _computeIsChannelDescriptionChangeable() {
            return this.model === 'mail.channel' && ['channel', 'group'].includes(this.channel_type);
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsChannelRenamable() {
            return (
                this.model === 'mail.channel' &&
                ['chat', 'channel', 'group'].includes(this.channel_type)
            );
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasMemberListFeature() {
            return this.model === 'mail.channel' && ['channel', 'group'].includes(this.channel_type);
        }

        /**
         * @returns {string}
         */
        _computeInvitationLink() {
            if (!this.uuid || !this.channel_type || this.channel_type === 'chat') {
                return clear();
            }
            return `${window.location.origin}/chat/${this.id}/${this.uuid}`;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsChatChannel() {
            return this.channel_type === 'chat' || this.channel_type === 'group';
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsCurrentPartnerFollowing() {
            return this.followers.some(follower =>
                follower.partner && follower.partner === this.messaging.currentPartner
            );
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsPinned() {
            return this.isPendingPinned !== undefined ? this.isPendingPinned : this.isServerPinned;
        }

        /**
         * @private
         * @returns {mail.message}
         */
        _computeLastCurrentPartnerMessageSeenByEveryone() {
            const otherPartnerSeenInfos =
                this.partnerSeenInfos.filter(partnerSeenInfo =>
                    partnerSeenInfo.partner !== this.messaging.currentPartner);
            if (otherPartnerSeenInfos.length === 0) {
                return unlinkAll();
            }

            const otherPartnersLastSeenMessageIds =
                otherPartnerSeenInfos.map(partnerSeenInfo =>
                    partnerSeenInfo.lastSeenMessage ? partnerSeenInfo.lastSeenMessage.id : 0
                );
            if (otherPartnersLastSeenMessageIds.length === 0) {
                return unlinkAll();
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
                return unlinkAll();
            }
            return link(currentPartnerOrderedSeenMessages.slice().pop());
        }

        /**
         * @private
         * @returns {mail.message|undefined}
         */
        _computeLastMessage() {
            const {
                length: l,
                [l - 1]: lastMessage,
            } = this.orderedMessages;
            if (lastMessage) {
                return link(lastMessage);
            }
            return unlink();
        }

        /**
         * @private
         * @returns {mail.message|undefined}
         */
        _computeLastNonTransientMessage() {
            const {
                length: l,
                [l - 1]: lastMessage,
            } = this.orderedNonTransientMessages;
            if (lastMessage) {
                return link(lastMessage);
            }
            return unlink();
        }

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
        }

        /**
         * @private
         * @returns {mail.message|undefined}
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
                return link(lastNeedactionMessageAsOriginThread);
            }
            return unlink();
        }

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
        }

        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMessagingAsRingingThread() {
            if (this.rtcInvitingSession) {
                return replace(this.messaging);
            }
            return clear();
        }

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
        }

        /**
         * @private
         * @returns {mail.message[]}
         */
        _computeNeedactionMessagesAsOriginThread() {
            return replace(this.messagesAsOriginThread.filter(message => message.isNeedaction));
        }

        /**
         * @private
         * @returns {mail.message|undefined}
         */
        _computeMessageAfterNewMessageSeparator() {
            if (this.model !== 'mail.channel') {
                return unlink();
            }
            if (this.localMessageUnreadCounter === 0) {
                return unlink();
            }
            const index = this.orderedMessages.findIndex(message =>
                message.id === this.lastSeenByCurrentPartnerMessageId
            );
            if (index === -1) {
                return unlink();
            }
            const message = this.orderedMessages[index + 1];
            if (!message) {
                return unlink();
            }
            return link(message);
        }

        /**
         * @private
         * @returns {mail.partner[]}
         */
        _computeOrderedOfflineMembers() {
            return replace(this._sortMembers(this.members.filter(member => !member.isOnline)));
        }

        /**
         * @private
         * @returns {mail.partner[]}
         */
        _computeOrderedOnlineMembers() {
            return replace(this._sortMembers(this.members.filter(member => member.isOnline)));
        }

        /**
         * @private
         * @returns {mail.message[]}
         */
        _computeOrderedMessages() {
            return replace(this.messages.sort((m1, m2) => m1.id < m2.id ? -1 : 1));
        }

        /**
         * @private
         * @returns {mail.message[]}
         */
        _computeOrderedNonTransientMessages() {
            return replace(this.orderedMessages.filter(m => !m.isTransient));
        }

        /**
         * @private
         * @returns {mail.partner[]}
         */
        _computeOrderedOtherTypingMembers() {
            return replace(this.orderedTypingMembers.filter(
                member => member !== this.messaging.currentPartner
            ));
        }

        /**
         * @private
         * @returns {mail.partner[]}
         */
        _computeOrderedTypingMembers() {
            return [[
                'replace',
                this.orderedTypingMemberLocalIds
                    .map(localId => this.messaging.models['mail.partner'].get(localId))
                    .filter(member => !!member),
            ]];
        }

        /**
         * @private
         * @returns {mail.activity[]}
         */
        _computeOverdueActivities() {
            return replace(this.activities.filter(activity => activity.state === 'overdue'));
        }

        /**
         * @private
         * @returns {mail.activity[]}
         */
        _computeTodayActivities() {
            return replace(this.activities.filter(activity => activity.state === 'today'));
        }

        /**
         * @private
         * @returns {string}
         */
        _computeTypingStatusText() {
            if (this.orderedOtherTypingMembers.length === 0) {
                return this.constructor.fields.typingStatusText.default;
            }
            if (this.orderedOtherTypingMembers.length === 1) {
                return _.str.sprintf(
                    this.env._t("%s is typing..."),
                    this.getMemberName(this.orderedOtherTypingMembers[0])
                );
            }
            if (this.orderedOtherTypingMembers.length === 2) {
                return _.str.sprintf(
                    this.env._t("%s and %s are typing..."),
                    this.getMemberName(this.orderedOtherTypingMembers[0]),
                    this.getMemberName(this.orderedOtherTypingMembers[1])
                );
            }
            return _.str.sprintf(
                this.env._t("%s, %s and more are typing..."),
                this.getMemberName(this.orderedOtherTypingMembers[0]),
                this.getMemberName(this.orderedOtherTypingMembers[1])
            );
        }

        /**
         * @private
         * @returns {integer}
         */
        _computeUnknownMemberCount() {
            return this.memberCount - this.members.length;
        }

        /**
         * Compute an url string that can be used inside a href attribute
         *
         * @private
         * @returns {string}
         */
        _computeUrl() {
            const baseHref = this.env.session.url('/web');
            if (this.model === 'mail.channel') {
                return `${baseHref}#action=mail.action_discuss&active_id=${this.model}_${this.id}`;
            }
            return `${baseHref}#model=${this.model}&id=${this.id}`;
        }

        /**
         * @private
         * @returns {number}
         */
        _computeVideoCount() {
            return this.rtcSessions.filter(session => session.videoStream).length;
        }

        /**
         * Returns the discuss sidebar category that corresponds to this channel
         * type.
         *
         * @private
         * @returns {mail.discuss_sidebar_category}
         */
        _getDiscussSidebarCategory() {
            switch (this.channel_type) {
                case 'channel':
                    return this.messaging.discuss.categoryChannel;
                case 'chat':
                case 'group':
                    return this.messaging.discuss.categoryChat;
            }
        }

        /**
         * @private
         * @param {Object} param0
         * @param {boolean} param0.isTyping
         */
        async _notifyCurrentPartnerTypingStatus({ isTyping }) {
            if (
                this._forceNotifyNextCurrentPartnerTypingStatus ||
                isTyping !== this._currentPartnerLastNotifiedIsTyping
            ) {
                if (this.model === 'mail.channel') {
                    await this.async(() => this.env.services.rpc({
                        model: 'mail.channel',
                        method: 'notify_typing',
                        args: [this.id],
                        kwargs: { is_typing: isTyping },
                    }, { shadow: true }));
                }
                if (isTyping && this._currentPartnerLongTypingTimer.isRunning) {
                    this._currentPartnerLongTypingTimer.reset();
                }
            }
            this._forceNotifyNextCurrentPartnerTypingStatus = false;
            this._currentPartnerLastNotifiedIsTyping = isTyping;
        }

        /**
         * @private
         */
        _onChangeLastSeenByCurrentPartnerMessageId() {
            this.messaging.messagingBus.trigger('o-thread-last-seen-by-current-partner-message-id-changed', {
                thread: this,
            });
        }

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
        }

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
            if (this.messaging.device.isMobile) {
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
        }

        /**
         * @private
         */
        _promptAddFollower() {
            const action = {
                type: 'ir.actions.act_window',
                res_model: 'mail.wizard.invite',
                view_mode: 'form',
                views: [[false, 'form']],
                name: this.env._t("Invite Follower"),
                target: 'new',
                context: {
                    default_res_model: this.model,
                    default_res_id: this.id,
                },
            };
            this.env.bus.trigger('do-action', {
                action,
                options: {
                    on_close: async () => {
                       await this.async(() => this.refreshFollowers());
                       this.env.bus.trigger('mail.thread:promptAddFollower-closed');
                    },
                },
            });
        }

        /**
         * @private
         * @param {mail.partner[]} members
         * @returns {mail.partner[]}
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
        }

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

        /**
         * Event handler for clicking thread in discuss app.
         */
        async onClick() {
            await this.open();
        }

        /**
         * Handles click on the "load more members" button.
         */
        async onClickLoadMoreMembers() {
            const members = await this.env.services.rpc({
                model: 'mail.channel',
                method: 'load_more_members',
                args: [[this.id]],
                kwargs: {
                    'known_member_ids': this.members.map(partner => partner.id),
                },
            });
            this.update({ members });
        }

        /**
         * @private
         */
        async _onCurrentPartnerInactiveTypingTimeout() {
            await this.async(() => this.unregisterCurrentPartnerIsTyping());
        }

        /**
         * Called when current partner has been typing for a very long time.
         * Immediately notify other members that he/she is still typing.
         *
         * @private
         */
        async _onCurrentPartnerLongTypingTimeout() {
            this._forceNotifyNextCurrentPartnerTypingStatus = true;
            this._throttleNotifyCurrentPartnerTypingStatus.clear();
            await this.async(
                () => this._throttleNotifyCurrentPartnerTypingStatus({ isTyping: true })
            );
        }

        /**
         * @private
         * @param {mail.partner} partner
         */
        async _onOtherMemberLongTypingTimeout(partner) {
            if (!this.typingMembers.includes(partner)) {
                this._otherMembersLongTypingTimers.delete(partner);
                return;
            }
            this.unregisterOtherMemberTypingMember(partner);
        }

    }

    Thread.fields = {
        /**
         * Determines the `mail.activity` that belong to `this`, assuming `this`
         * has activities (@see hasActivities).
         */
        activities: one2many('mail.activity', {
            inverse: 'thread',
        }),
        allAttachments: many2many('mail.attachment', {
            compute: '_computeAllAttachments',
        }),
        areAttachmentsLoaded: attr({
            default: false,
        }),
        /**
         * States whether followers have been loaded at least once for this
         * thread.
         */
        areFollowersLoaded: attr({
            default: false,
        }),
        attachments: many2many('mail.attachment', {
            inverse: 'threads',
        }),
        /**
         * Cache key to force a reload of the avatar when avatar is changed.
         * It only makes sense for channels.
         */
        avatarCacheKey: attr(),
        cache: one2one('mail.thread_cache', {
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
        chatWindow: one2one('mail.chat_window', {
            inverse: 'thread',
            isCausal: true,
        }),
        /**
         * Determines the composer state of this thread.
         */
        composer: one2one('mail.composer', {
            compute: '_computeComposer',
            inverse: 'thread',
            isCausal: true,
            readonly: true,
        }),
        correspondent: many2one('mail.partner', {
            compute: '_computeCorrespondent',
        }),
        counter: attr({
            default: 0,
        }),
        creator: many2one('mail.user'),
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
        discussSidebarCategoryItem: one2one('mail.discuss_sidebar_category_item', {
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
        followersPartner: many2many('mail.partner', {
            related: 'followers.partner',
        }),
        followers: one2many('mail.follower', {
            inverse: 'followedThread',
        }),
        /**
         * States the `mail.activity` that belongs to `this` and that are
         * planned in the future (due later than today).
         */
        futureActivities: one2many('mail.activity', {
            compute: '_computeFutureActivities',
        }),
        group_based_subscription: attr({
            default: false,
        }),
        guestMembers: many2many('mail.guest'),
        /**
         * States whether `this` has activities (`mail.activity.mixin` server side).
         */
        hasActivities: attr({
            default: false,
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
        invitedGuests: many2many('mail.guest'),
        /**
         * List of partners that have been invited to the RTC call of this channel.
         */
        invitedPartners: many2many('mail.partner'),
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
        lastCurrentPartnerMessageSeenByEveryone: many2one('mail.message', {
            compute: '_computeLastCurrentPartnerMessageSeenByEveryone',
        }),
        /**
         * Last message of the thread, could be a transient one.
         */
        lastMessage: many2one('mail.message', {
            compute: '_computeLastMessage',
        }),
        /**
         * States the last known needaction message having this thread as origin.
         */
        lastNeedactionMessageAsOriginThread: many2one('mail.message', {
            compute: '_computeLastNeedactionMessageAsOriginThread',
        }),
        /**
         * Last non-transient message.
         */
        lastNonTransientMessage: many2one('mail.message', {
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
        members: many2many('mail.partner', {
            inverse: 'memberThreads',
        }),
        /**
         * Determines the last mentioned channels of the last composer related
         * to this thread. Useful to sync the composer when re-creating it.
         */
        mentionedChannelsBackup: many2many('mail.thread'),
        /**
         * Determines the last mentioned partners of the last composer related
         * to this thread. Useful to sync the composer when re-creating it.
         */
        mentionedPartnersBackup: many2many('mail.partner'),
        /**
         * Determines the message before which the "new message" separator must
         * be positioned, if any.
         */
        messageAfterNewMessageSeparator: many2one('mail.message', {
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
        messages: many2many('mail.message', {
            inverse: 'threads',
            readonly: true,
        }),
        /**
         * All messages that have been originally posted in this thread.
         */
        messagesAsOriginThread: one2many('mail.message', {
            inverse: 'originThread',
            isCausal: true,
        }),
        /**
         * Contains the message fetched/seen indicators for all messages of this thread.
         */
        messageSeenIndicators: one2many('mail.message_seen_indicator', {
            inverse: 'thread',
            isCausal: true,
        }),
        messagingAsRingingThread: many2one('mail.messaging', {
            compute: '_computeMessagingAsRingingThread',
            inverse: 'ringingThreads',
            readonly: true,
        }),
        messagingMenuAsPinnedAndUnreadChannel: many2one('mail.messaging_menu', {
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
        needactionMessagesAsOriginThread: many2many('mail.message', {
            compute: '_computeNeedactionMessagesAsOriginThread',
        }),
        /**
         * All offline members ordered like they are displayed.
         */
        orderedOfflineMembers: many2many('mail.partner', {
            compute: '_computeOrderedOfflineMembers',
        }),
        /**
         * All online members ordered like they are displayed.
         */
        orderedOnlineMembers: many2many('mail.partner', {
            compute: '_computeOrderedOnlineMembers',
        }),
        /**
         * All messages ordered like they are displayed.
         */
        orderedMessages: many2many('mail.message', {
            compute: '_computeOrderedMessages',
        }),
        /**
         * All messages ordered like they are displayed. This field does not
         * contain transient messages which are not "real" records.
         */
        orderedNonTransientMessages: many2many('mail.message', {
            compute: '_computeOrderedNonTransientMessages',
        }),
        /**
         * Ordered typing members on this thread, excluding the current partner.
         */
        orderedOtherTypingMembers: many2many('mail.partner', {
            compute: '_computeOrderedOtherTypingMembers',
        }),
        /**
         * Ordered typing members on this thread. Lower index means this member
         * is currently typing for the longest time. This list includes current
         * partner as typer.
         */
        orderedTypingMembers: many2many('mail.partner', {
            compute: '_computeOrderedTypingMembers',
        }),
        /**
         * Technical attribute to manage ordered list of typing members.
         */
        orderedTypingMemberLocalIds: attr({
            default: [],
        }),
        originThreadAttachments: one2many('mail.attachment', {
            inverse: 'originThread',
            isCausal: true,
        }),
        /**
         * States the `mail.activity` that belongs to `this` and that are
         * overdue (due earlier than today).
         */
        overdueActivities: one2many('mail.activity', {
            compute: '_computeOverdueActivities',
        }),
        /**
         * Contains the seen information for all members of the thread.
         * FIXME This field should be readonly once task-2336946 is done.
         */
        partnerSeenInfos: one2many('mail.thread_partner_seen_info', {
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
        rtc: one2one('mail.rtc', {
            inverse: 'channel',
        }),
        /**
         * The session that invited the current user, it is only set when the
         * invitation is still pending.
         */
        rtcInvitingSession: many2one('mail.rtc_session', {
            inverse: 'calledChannels',
        }),
        rtcSessions: one2many('mail.rtc_session', {
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
        serverLastMessage: many2one('mail.message'),
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
         * Determines the `mail.suggested_recipient_info` concerning `this`.
         */
        suggestedRecipientInfoList: one2many('mail.suggested_recipient_info', {
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
        threadViews: one2many('mail.thread_view', {
            inverse: 'thread',
        }),
        /**
         * States the `mail.activity` that belongs to `this` and that are due
         * specifically today.
         */
        todayActivities: one2many('mail.activity', {
            compute: '_computeTodayActivities',
        }),
        /**
         * Members that are currently typing something in the composer of this
         * thread, including current partner.
         */
        typingMembers: many2many('mail.partner'),
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
    };
    Thread.identifyingFields = ['model', 'id'];
    Thread.onChanges = [
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
    ];
    Thread.modelName = 'mail.thread';

    return Thread;
}

registerNewModel('mail.thread', factory);
