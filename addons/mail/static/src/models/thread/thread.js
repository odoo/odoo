odoo.define('mail/static/src/models/thread/thread.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2many, many2one, one2many, one2one } = require('mail/static/src/model/model_field.js');
const { clear } = require('mail/static/src/model/model_field_command.js');
const throttle = require('mail/static/src/utils/throttle/throttle.js');
const Timer = require('mail/static/src/utils/timer/timer.js');
const mailUtils = require('mail.utils');

function factory(dependencies) {

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
                () => this.async(() => this._onCurrentPartnerInactiveTypingTimeout()),
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
         * @static
         * @param {mail.thread} [thread] the concerned thread
         */
        static computeLastCurrentPartnerMessageSeenByEveryone(thread = undefined) {
            const threads = thread ? [thread] : this.env.models['mail.thread'].all();
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
            const data2 = {
                messagesAsServerChannel: [],
            };
            if ('model' in data) {
                data2.model = data.model;
            }
            if ('channel_type' in data) {
                data2.channel_type = data.channel_type;
                data2.model = 'mail.channel';
            }
            if ('create_uid' in data) {
                data2.creator = [['insert', { id: data.create_uid }]];
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
            if ('is_minimized' in data && 'state' in data) {
                data2.serverFoldState = data.is_minimized ? data.state : 'closed';
            }
            if ('is_moderator' in data) {
                data2.is_moderator = data.is_moderator;
            }
            if ('is_pinned' in data) {
                data2.isServerPinned = data.is_pinned;
            }
            if ('last_message' in data && data.last_message) {
                data2.messagesAsServerChannel.push(['insert', { id: data.last_message.id }]);
                data2.serverLastMessageId = data.last_message.id;
            }
            if ('last_message_id' in data && data.last_message_id) {
                data2.messagesAsServerChannel.push(['insert', { id: data.last_message_id }]);
                data2.serverLastMessageId = data.last_message_id;
            }
            if ('mass_mailing' in data) {
                data2.mass_mailing = data.mass_mailing;
            }
            if ('moderation' in data) {
                data2.moderation = data.moderation;
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
                if (!data.members) {
                    data2.members = [['unlink-all']];
                } else {
                    data2.members = [
                        ['insert-and-replace', data.members.map(memberData =>
                            this.env.models['mail.partner'].convertData(memberData)
                        )],
                    ];
                }
            }
            if ('seen_partners_info' in data) {
                if (!data.seen_partners_info) {
                    data2.partnerSeenInfos = [['unlink-all']];
                } else {
                    /*
                     * FIXME: not optimal to write on relation given the fact that the relation
                     * will be (re)computed based on given fields.
                     * (here channelId will compute partnerSeenInfo.thread))
                     * task-2336946
                     */
                    data2.partnerSeenInfos = [
                        ['insert-and-replace',
                            data.seen_partners_info.map(
                                ({ fetched_message_id, partner_id, seen_message_id }) => {
                                    return {
                                        channelId: data2.id,
                                        lastFetchedMessage: [fetched_message_id ? ['insert', { id: fetched_message_id }] : ['unlink-all']],
                                        lastSeenMessage: [seen_message_id ? ['insert', { id: seen_message_id }] : ['unlink-all']],
                                        partnerId: partner_id,
                                    };
                                })
                        ]
                    ];
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
                            /*
                             * FIXME: not optimal to write on relation given the fact that the relation
                             * will be (re)computed based on given fields.
                             * (here channelId will compute messageSeenIndicator.thread))
                             * task-2336946
                             */
                            data2.messageSeenIndicators = [
                                ['insert',
                                    [...messageIds].map(messageId => {
                                       return {
                                           channelId: data.id || this.id,
                                           messageId,
                                       };
                                    })
                                ]
                            ];
                        }
                    }
                }
            }

            return data2;
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
            this.env.models['mail.message'].insert(channelPreviews.filter(p => p.last_message).map(
                channelPreview => this.env.models['mail.message'].convertData(channelPreview.last_message)
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
            const channels = this.env.models['mail.thread'].insert(
                channelInfos.map(channelInfo => this.env.models['mail.thread'].convertData(channelInfo))
            );
            // manually force recompute of counter
            this.env.messaging.messagingMenu.update();
            return channels;
        }

        /**
         * Performs the `channel_seen` RPC on `mail.channel`.
         *
         * @static
         * @param {Object} param0
         * @param {integer[]} param0.ids list of id of channels
         * @param {integer[]} param0.lastMessageId
         */
        static async performRpcChannelSeen({ ids, lastMessageId }) {
            return this.env.services.rpc({
                model: 'mail.channel',
                method: 'channel_seen',
                args: [ids],
                kwargs: {
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
            const device = this.env.messaging.device;
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
            return this.env.models['mail.thread'].insert(
                this.env.models['mail.thread'].convertData(data)
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
            const device = this.env.messaging.device;
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
            return this.env.models['mail.thread'].insert(
                this.env.models['mail.thread'].convertData(data)
            );
        }

        /**
         * Performs the `channel_join_and_get_info` RPC on `mail.channel`.
         *
         * @static
         * @param {Object} param0
         * @param {integer} param0.channelId
         * @returns {mail.thread} the channel that was joined
         */
        static async performRpcJoinChannel({ channelId }) {
            const device = this.env.messaging.device;
            const data = await this.env.services.rpc({
                model: 'mail.channel',
                method: 'channel_join_and_get_info',
                args: [[channelId]],
                kwargs: {
                    context: Object.assign({}, this.env.session.user_content, {
                        // optimize the return value by avoiding useless queries
                        // in non-mobile devices
                        isMobile: device.isMobile,
                    }),
                },
            });
            return this.env.models['mail.thread'].insert(
                this.env.models['mail.thread'].convertData(data)
            );
        }

        /**
         * Performs the `execute_command` RPC on `mail.channel`.
         *
         * @static
         * @param {Object} param0
         * @param {integer} param0.channelId
         * @param {string} param0.command
         * @param {Object} [param0.postData={}]
         */
        static async performRpcExecuteCommand({ channelId, command, postData = {} }) {
            return this.env.services.rpc({
                model: 'mail.channel',
                method: 'execute_command',
                args: [[channelId]],
                kwargs: Object.assign({ command }, postData),
            });
        }

        /**
         * Performs the `message_post` RPC on given threadModel.
         *
         * @static
         * @param {Object} param0
         * @param {Object} param0.postData
         * @param {integer} param0.threadId
         * @param {string} param0.threadModel
         * @return {integer} the posted message id
         */
        static async performRpcMessagePost({ postData, threadId, threadModel }) {
            return this.env.services.rpc({
                model: threadModel,
                method: 'message_post',
                args: [threadId],
                kwargs: postData,
            });
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
                        name,
                        partner: [partner_id ? ['insert', { id: partner_id }] : ['unlink']],
                        reason,
                    };
                });
                this.insert({
                    id: parseInt(id),
                    model,
                    suggestedRecipientInfoList: [['insert-and-replace', recipientInfoList]],
                });
            }
        }

        /**
         * @param {string} [stringifiedDomain='[]']
         * @returns {mail.thread_cache}
         */
        cache(stringifiedDomain = '[]') {
            return this.env.models['mail.thread_cache'].insert({
                stringifiedDomain,
                thread: [['link', this]],
            });
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
                originThreadAttachments: [['insert-and-replace',
                    attachmentsData.map(data =>
                        this.env.models['mail.attachment'].convertData(data)
                    )
                ]],
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
            return this.env.models['mail.thread'].performRpcMailGetSuggestedRecipients({
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
                    partner_ids: [this.env.messaging.currentPartner.id],
                    context: {}, // FIXME empty context to be overridden in session.js with 'allowed_company_ids' task-2243187
                },
            }));
            this.refreshFollowers();
            this.fetchAndUpdateSuggestedRecipients();
        }

        /**
         * Load new messages on the main cache of this thread.
         */
        loadNewMessages() {
            this.mainCache.loadNewMessages();
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
            return this.env.models['mail.thread'].performRpcChannelSeen({
                ids: [this.id],
                lastMessageId: message.id,
            });
        }

        /**
         * Marks as read all needaction messages with this thread as origin.
         */
        async markNeedactionMessagesAsOriginThreadAsRead() {
            await this.async(() =>
                this.env.models['mail.message'].markAsRead(this.needactionMessagesAsOriginThread)
            );
        }

        /**
         * Mark as read all needaction messages of this thread.
         */
        async markNeedactionMessagesAsRead() {
            await this.async(() =>
                this.env.models['mail.message'].markAsRead(this.needactionMessages)
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
            return this.env.models['mail.thread'].performRpcChannelFold(this.uuid, state);
        }

        /**
         * Notify server to leave the current channel. Useful for cross-tab
         * and cross-device chat window state synchronization.
         *
         * Only makes sense if isPendingPinned is set to the desired value.
         */
        async notifyPinStateToServer() {
            if (this.isPendingPinned) {
                await this.env.models['mail.thread'].performRpcChannelPin({
                    pinned: true,
                    uuid: this.uuid,
                });
            } else {
                this.env.models['mail.thread'].performRpcExecuteCommand({
                    channelId: this.id,
                    command: 'leave',
                });
            }
        }

        /**
         * Opens this thread either as form view, in discuss app, or as a chat
         * window. The thread will be opened in an "active" matter, which will
         * interrupt current user flow.
         *
         * @param {Object} [param0]
         * @param {boolean} [param0.expanded=false]
         */
        async open({ expanded = false } = {}) {
            const discuss = this.env.messaging.discuss;
            // check if thread must be opened in form view
            if (!['mail.box', 'mail.channel'].includes(this.model)) {
                if (expanded || discuss.isOpen) {
                    // Close chat window because having the same thread opened
                    // both in chat window and as main document does not look
                    // good.
                    this.env.messaging.chatWindowManager.closeThread(this);
                    return this.env.messaging.openDocument({
                        id: this.id,
                        model: this.model,
                    });
                }
            }
            // check if thread must be opened in discuss
            const device = this.env.messaging.device;
            if (
                (!device.isMobile && (discuss.isOpen || expanded)) ||
                this.model === 'mail.box'
            ) {
                return discuss.openThread(this);
            }
            // thread must be opened in chat window
            return this.env.messaging.chatWindowManager.openThread(this, {
                makeActive: true,
            });
        }

        /**
         * Opens the most appropriate view that is a profile for this thread.
         */
        async openProfile() {
            return this.env.messaging.openDocument({
                id: this.id,
                model: this.model,
            });
        }

        /**
         * Pin this thread and notify server of the change.
         */
        async pin() {
            this.update({ isPendingPinned: true });
            await this.notifyPinStateToServer();
        }

        /**
         * Open a dialog to add channels as followers.
         */
        promptAddChannelFollower() {
            this._promptAddFollower({ mail_invite_follower_channel_only: true });
        }

        /**
         * Open a dialog to add partners as followers.
         */
        promptAddPartnerFollower() {
            this._promptAddFollower({ mail_invite_follower_channel_only: false });
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
            const activities = this.env.models['mail.activity'].insert(activitiesData.map(
                activityData => this.env.models['mail.activity'].convertData(activityData)
            ));
            this.update({ activities: [['replace', activities]] });
        }

        /**
         * Refresh followers information from server.
         */
        async refreshFollowers() {
            if (this.isTemporary) {
                this.update({ followers: [['unlink-all']] });
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
                    followers: [['insert-and-replace', followers.map(data =>
                        this.env.models['mail.follower'].convertData(data))
                    ]],
                });
            } else {
                this.update({
                    followers: [['unlink-all']],
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
            const currentPartner = this.env.messaging.currentPartner;
            const newOrderedTypingMemberLocalIds = this.orderedTypingMemberLocalIds
                .filter(localId => localId !== currentPartner.localId);
            newOrderedTypingMemberLocalIds.push(currentPartner.localId);
            this.update({
                orderedTypingMemberLocalIds: newOrderedTypingMemberLocalIds,
                typingMembers: [['link', currentPartner]],
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
                typingMembers: [['link', partner]],
            });
        }

        /**
         * Rename the given thread with provided new name.
         *
         * @param {string} newName
         */
        async rename(newName) {
            if (this.channel_type === 'chat') {
                await this.async(() => this.env.services.rpc({
                    model: 'mail.channel',
                    method: 'channel_set_custom_name',
                    args: [this.id],
                    kwargs: {
                        name: newName,
                    },
                }));
            }
            this.update({ custom_channel_name: newName });
        }

        /**
         * Unfollow current partner from this thread.
         */
        async unfollow() {
            const currentPartnerFollower = this.followers.find(
                follower => follower.partner === this.env.messaging.currentPartner
            );
            await this.async(() => currentPartnerFollower.remove());
        }

        /**
         * Unpin this thread and notify server of the change.
         */
        async unpin() {
            this.update({ isPendingPinned: false });
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
            const currentPartner = this.env.messaging.currentPartner;
            const newOrderedTypingMemberLocalIds = this.orderedTypingMemberLocalIds
                .filter(localId => localId !== currentPartner.localId);
            this.update({
                orderedTypingMemberLocalIds: newOrderedTypingMemberLocalIds,
                typingMembers: [['unlink', currentPartner]],
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
                typingMembers: [['unlink', partner]],
            });
        }

        /**
         * Unsubscribe current user from provided channel.
         */
        unsubscribe() {
            this.env.messaging.chatWindowManager.closeThread(this);
            this.unpin();
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            const { channel_type, id, model } = data;
            let threadModel = model;
            if (!threadModel && channel_type) {
                threadModel = 'mail.channel';
            }
            return `${this.modelName}_${threadModel}_${id}`;
        }

        /**
         * @private
         * @returns {mail.attachment[]}
         */
        _computeAllAttachments() {
            const allAttachments = [...new Set(this.originThreadAttachments.concat(this.attachments))]
                .sort((a1, a2) => {
                    // "uploading" before "uploaded" attachments.
                    if (!a1.isTemporary && a2.isTemporary) {
                        return 1;
                    }
                    if (a1.isTemporary && !a2.isTemporary) {
                        return -1;
                    }
                    // "most-recent" before "oldest" attachments.
                    return Math.abs(a2.id) - Math.abs(a1.id);
                });
            return [['replace', allAttachments]];
        }

        /**
         * @private
         * @returns {mail.partner}
         */
        _computeCorrespondent() {
            if (this.channel_type === 'channel') {
                return [['unlink']];
            }
            const correspondents = this.members.filter(partner =>
                partner !== this.env.messaging.currentPartner
            );
            if (correspondents.length === 1) {
                // 2 members chat
                return [['link', correspondents[0]]];
            }
            if (this.members.length === 1) {
                // chat with oneself
                return [['link', this.members[0]]];
            }
            return [['unlink']];
        }

        /**
         * @private
         * @returns {string}
         */
        _computeDisplayName() {
            if (this.channel_type === 'chat' && this.correspondent) {
                return this.custom_channel_name || this.correspondent.nameOrDisplayName;
            }
            return this.name;
        }

        /**
         * @private
         * @returns {mail.activity[]}
         */
        _computeFutureActivities() {
            return [['replace', this.activities.filter(activity => activity.state === 'planned')]];
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasSeenIndicators() {
            if (this.model !== 'mail.channel') {
                return false;
            }
            if (this.mass_mailing) {
                return false;
            }
            return ['chat', 'livechat'].includes(this.channel_type);
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsChatChannel() {
            return this.channel_type === 'chat';
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsCurrentPartnerFollowing() {
            return this.followers.some(follower =>
                follower.partner && follower.partner === this.env.messaging.currentPartner
            );
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsModeratedByCurrentPartner() {
            if (!this.messaging) {
                return false;
            }
            if (!this.messaging.currentPartner) {
                return false;
            }
            return this.moderators.includes(this.env.messaging.currentPartner);
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
                    partnerSeenInfo.partner !== this.messagingCurrentPartner);
            if (otherPartnerSeenInfos.length === 0) {
                return [['unlink-all']];
            }

            const otherPartnersLastSeenMessageIds =
                otherPartnerSeenInfos.map(partnerSeenInfo =>
                    partnerSeenInfo.lastSeenMessage ? partnerSeenInfo.lastSeenMessage.id : 0
                );
            if (otherPartnersLastSeenMessageIds.length === 0) {
                return [['unlink-all']];
            }
            const lastMessageSeenByAllId = Math.min(
                ...otherPartnersLastSeenMessageIds
            );
            const currentPartnerOrderedSeenMessages =
                this.orderedNonTransientMessages.filter(message =>
                    message.author === this.messagingCurrentPartner &&
                    message.id <= lastMessageSeenByAllId);

            if (
                !currentPartnerOrderedSeenMessages ||
                currentPartnerOrderedSeenMessages.length === 0
            ) {
                return [['unlink-all']];
            }
            return [['link', currentPartnerOrderedSeenMessages.slice().pop()]];
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
                return [['link', lastMessage]];
            }
            return [['unlink']];
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
                return [['link', lastMessage]];
            }
            return [['unlink']];
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
                    message.author === this.env.messaging.currentPartner ||
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
        _computeLastNeedactionMessage() {
            const orderedNeedactionMessages = this.needactionMessages.sort(
                (m1, m2) => m1.id < m2.id ? -1 : 1
            );
            const {
                length: l,
                [l - 1]: lastNeedactionMessage,
            } = orderedNeedactionMessages;
            if (lastNeedactionMessage) {
                return [['link', lastNeedactionMessage]];
            }
            return [['unlink']];
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
                return [['link', lastNeedactionMessageAsOriginThread]];
            }
            return [['unlink']];
        }

        /**
         * @private
         * @returns {mail.thread_cache}
         */
        _computeMainCache() {
            return [['link', this.cache()]];
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
            let countFromId = this.serverLastMessageId;
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
         * @returns {mail.messaging}
         */
        _computeMessaging() {
            return [['link', this.env.messaging]];
        }

        /**
         * @private
         * @returns {mail.message[]}
         */
        _computeNeedactionMessages() {
            return [['replace', this.messages.filter(message => message.isNeedaction)]];
        }

        /**
         * @private
         * @returns {mail.message[]}
         */
        _computeNeedactionMessagesAsOriginThread() {
            return [['replace', this.messagesAsOriginThread.filter(message => message.isNeedaction)]];
        }

        /**
         * @private
         * @returns {mail.message|undefined}
         */
        _computeMessageAfterNewMessageSeparator() {
            if (this.model !== 'mail.channel') {
                return [['unlink']];
            }
            if (this.localMessageUnreadCounter === 0) {
                return [['unlink']];
            }
            const index = this.orderedMessages.findIndex(message =>
                message.id === this.lastSeenByCurrentPartnerMessageId
            );
            if (index === -1) {
                return [['unlink']];
            }
            const message = this.orderedMessages[index + 1];
            if (!message) {
                return [['unlink']];
            }
            return [['link', message]];
        }

        /**
         * @private
         * @returns {mail.message[]}
         */
        _computeOrderedMessages() {
            return [['replace', this.messages.sort((m1, m2) => m1.id < m2.id ? -1 : 1)]];
        }

        /**
         * @private
         * @returns {mail.message[]}
         */
        _computeOrderedNonTransientMessages() {
            return [['replace', this.orderedMessages.filter(m => !m.isTransient)]];
        }

        /**
         * @private
         * @returns {mail.partner[]}
         */
        _computeOrderedOtherTypingMembers() {
            return [[
                'replace',
                this.orderedTypingMembers.filter(
                    member => member !== this.env.messaging.currentPartner
                ),
            ]];
        }

        /**
         * @private
         * @returns {mail.partner[]}
         */
        _computeOrderedTypingMembers() {
            return [[
                'replace',
                this.orderedTypingMemberLocalIds
                    .map(localId => this.env.models['mail.partner'].get(localId))
                    .filter(member => !!member),
            ]];
        }

        /**
         * @private
         * @returns {mail.activity[]}
         */
        _computeOverdueActivities() {
            return [['replace', this.activities.filter(activity => activity.state === 'overdue')]];
        }

        /**
         * @private
         * @returns {mail.activity[]}
         */
        _computeTodayActivities() {
            return [['replace', this.activities.filter(activity => activity.state === 'today')]];
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
                    this.orderedOtherTypingMembers[0].nameOrDisplayName
                );
            }
            if (this.orderedOtherTypingMembers.length === 2) {
                return _.str.sprintf(
                    this.env._t("%s and %s are typing..."),
                    this.orderedOtherTypingMembers[0].nameOrDisplayName,
                    this.orderedOtherTypingMembers[1].nameOrDisplayName
                );
            }
            return _.str.sprintf(
                this.env._t("%s, %s and more are typing..."),
                this.orderedOtherTypingMembers[0].nameOrDisplayName,
                this.orderedOtherTypingMembers[1].nameOrDisplayName
            );
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
         * Cleans followers of current thread. In particular, chats are supposed
         * to work with "members", not with "followers". This clean up is only
         * necessary to remove illegitimate followers in stable version, it can
         * be removed in master after proper migration to clean the database.
         *
         * @private
         */
        _onChangeFollowersPartner() {
            if (this.channel_type !== 'chat') {
                return;
            }
            for (const follower of this.followers) {
                if (follower.partner) {
                    follower.remove();
                }
            }
        }

        /**
         * @private
         */
        _onChangeLastSeenByCurrentPartnerMessageId() {
            this.env.messagingBus.trigger('o-thread-last-seen-by-current-partner-message-id-changed', {
                thread: this,
            });
        }

        /**
         * @private
         */
        _onChangeThreadViews() {
            if (this.threadViews.length === 0) {
                return;
            }
            /**
             * Fetches followers of chats when they are displayed for the first
             * time. This is necessary to clean the followers.
             * @see `_onChangeFollowersPartner` for more information.
             */
            if (this.channel_type === 'chat' && !this.areFollowersLoaded) {
                this.refreshFollowers();
            }
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
            if (!this.env.messaging.chatWindowManager) {
                // avoid crash during destroy
                return;
            }
            if (this.env.messaging.device.isMobile) {
                return;
            }
            if (this.serverFoldState === 'closed') {
                this.env.messaging.chatWindowManager.closeThread(this, {
                    notifyServer: false,
                });
            } else {
                this.env.messaging.chatWindowManager.openThread(this, {
                    isFolded: this.serverFoldState === 'folded',
                    notifyServer: false,
                });
            }
        }

        /**
         * @private
         * @param {Object} [param0={}]
         * @param {boolean} [param0.mail_invite_follower_channel_only=false]
         */
        _promptAddFollower({ mail_invite_follower_channel_only = false } = {}) {
            const self = this;
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
                    mail_invite_follower_channel_only,
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

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

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
        /**
         * Serves as compute dependency.
         */
        activitiesState: attr({
            related: 'activities.state',
        }),
        allAttachments: many2many('mail.attachment', {
            compute: '_computeAllAttachments',
            dependencies: [
                'attachments',
                'originThreadAttachments',
            ],
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
        caches: one2many('mail.thread_cache', {
            inverse: 'thread',
            isCausal: true,
        }),
        channel_type: attr(),
        /**
         * States the `mail.chat_window` related to `this`. Serves as compute
         * dependency. It is computed from the inverse relation and it should
         * otherwise be considered read-only.
         */
        chatWindow: one2one('mail.chat_window', {
            inverse: 'thread',
        }),
        /**
         * Serves as compute dependency.
         */
        chatWindowIsFolded: attr({
            related: 'chatWindow.isFolded',
        }),
        composer: one2one('mail.composer', {
            default: [['create']],
            inverse: 'thread',
            isCausal: true,
        }),
        correspondent: many2one('mail.partner', {
            compute: '_computeCorrespondent',
            dependencies: [
                'channel_type',
                'members',
                'messagingCurrentPartner',
            ],
            inverse: 'correspondentThreads',
        }),
        correspondentNameOrDisplayName: attr({
            related: 'correspondent.nameOrDisplayName',
        }),
        counter: attr({
            default: 0,
        }),
        creator: many2one('mail.user'),
        custom_channel_name: attr(),
        displayName: attr({
            compute: '_computeDisplayName',
            dependencies: [
                'channel_type',
                'correspondent',
                'correspondentNameOrDisplayName',
                'custom_channel_name',
                'name',
            ],
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
            dependencies: ['activitiesState'],
        }),
        group_based_subscription: attr({
            default: false,
        }),
        /**
         * States whether `this` has activities (`mail.activity.mixin` server side).
         */
        hasActivities: attr({
            default: false,
        }),
        /**
         * Determine whether this thread has the seen indicators (V and VV)
         * enabled or not.
         */
        hasSeenIndicators: attr({
            compute: '_computeHasSeenIndicators',
            default: false,
            dependencies: [
                'channel_type',
                'mass_mailing',
                'model',
            ],
        }),
        id: attr(),
        /**
         * States whether this thread is a `mail.channel` qualified as chat.
         *
         * Useful to list chat channels, like in messaging menu with the filter
         * 'chat'.
         */
        isChatChannel: attr({
            compute: '_computeIsChatChannel',
            dependencies: [
                'channel_type',
            ],
            default: false,
        }),
        isCurrentPartnerFollowing: attr({
            compute: '_computeIsCurrentPartnerFollowing',
            default: false,
            dependencies: [
                'followersPartner',
                'messagingCurrentPartner',
            ],
        }),
        /**
         * States whether `this` is currently loading attachments.
         */
        isLoadingAttachments: attr({
            default: false,
        }),
        isModeratedByCurrentPartner: attr({
            compute: '_computeIsModeratedByCurrentPartner',
            dependencies: [
                'messagingCurrentPartner',
                'moderators',
            ],
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
            dependencies: [
                'isPendingPinned',
                'isServerPinned',
            ],
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
        is_moderator: attr({
            default: false,
        }),
        lastCurrentPartnerMessageSeenByEveryone: many2one('mail.message', {
            compute: '_computeLastCurrentPartnerMessageSeenByEveryone',
            dependencies: [
                'messagingCurrentPartner',
                'orderedNonTransientMessages',
                'partnerSeenInfos',
            ],
        }),
        /**
         * Last message of the thread, could be a transient one.
         */
        lastMessage: many2one('mail.message', {
            compute: '_computeLastMessage',
            dependencies: ['orderedMessages'],
        }),
        lastNeedactionMessage: many2one('mail.message', {
            compute: '_computeLastNeedactionMessage',
            dependencies: ['needactionMessages'],
        }),
        /**
         * States the last known needaction message having this thread as origin.
         */
        lastNeedactionMessageAsOriginThread: many2one('mail.message', {
            compute: '_computeLastNeedactionMessageAsOriginThread',
            dependencies: [
                'needactionMessagesAsOriginThread',
            ],
        }),
        /**
         * Last non-transient message.
         */
        lastNonTransientMessage: many2one('mail.message', {
            compute: '_computeLastNonTransientMessage',
            dependencies: ['orderedNonTransientMessages'],
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
            dependencies: [
                'lastSeenByCurrentPartnerMessageId',
                'messagingCurrentPartner',
                'orderedMessages',
                'orderedMessagesIsTransient',
                // FIXME missing dependency 'orderedMessages.author', (task-2261221)
            ],
        }),
        /**
         * Local value of message unread counter, that means it is based on initial server value and
         * updated with interface updates.
         */
        localMessageUnreadCounter: attr({
            compute: '_computeLocalMessageUnreadCounter',
            dependencies: [
                'lastSeenByCurrentPartnerMessageId',
                'messagingCurrentPartner',
                'orderedMessages',
                'serverLastMessageId',
                'serverMessageUnreadCounter',
            ],
        }),
        mainCache: one2one('mail.thread_cache', {
            compute: '_computeMainCache',
        }),
        mass_mailing: attr({
            default: false,
        }),
        members: many2many('mail.partner', {
            inverse: 'memberThreads',
        }),
        /**
         * Determines the message before which the "new message" separator must
         * be positioned, if any.
         */
        messageAfterNewMessageSeparator: many2one('mail.message', {
            compute: '_computeMessageAfterNewMessageSeparator',
            dependencies: [
                'lastSeenByCurrentPartnerMessageId',
                'localMessageUnreadCounter',
                'model',
                'orderedMessages',
            ],
        }),
        message_needaction_counter: attr({
            default: 0,
        }),
        /**
         * All messages that this thread is linked to.
         * Note that this field is automatically computed by inverse
         * computed field. This field is readonly.
         */
        messages: many2many('mail.message', {
            inverse: 'threads',
        }),
        /**
         * All messages that have been originally posted in this thread.
         */
        messagesAsOriginThread: one2many('mail.message', {
            inverse: 'originThread',
        }),
        /**
         * Serves as compute dependency.
         */
        messagesAsOriginThreadIsNeedaction: attr({
            related: 'messagesAsOriginThread.isNeedaction',
        }),
        /**
         * All messages that are contained on this channel on the server.
         * Equivalent to the inverse of python field `channel_ids`.
         */
        messagesAsServerChannel: many2many('mail.message', {
            inverse: 'serverChannels',
        }),
        /**
         * Serves as compute dependency.
         */
        messagesIsNeedaction: attr({
            related: 'messages.isNeedaction',
        }),
        messageSeenIndicators: one2many('mail.message_seen_indicator', {
            inverse: 'thread',
            isCausal: true,
        }),
        messaging: many2one('mail.messaging', {
            compute: '_computeMessaging',
        }),
        messagingCurrentPartner: many2one('mail.partner', {
            related: 'messaging.currentPartner',
        }),
        model: attr(),
        model_name: attr(),
        moderation: attr({
            default: false,
        }),
        /**
         * Partners that are moderating this thread (only applies to channels).
         */
        moderators: many2many('mail.partner', {
            inverse: 'moderatedChannels',
        }),
        moduleIcon: attr(),
        name: attr(),
        needactionMessages: many2many('mail.message', {
            compute: '_computeNeedactionMessages',
            dependencies: [
                'messages',
                'messagesIsNeedaction',
            ],
        }),
        /**
         * States all known needaction messages having this thread as origin.
         */
        needactionMessagesAsOriginThread: many2many('mail.message', {
            compute: '_computeNeedactionMessagesAsOriginThread',
            dependencies: [
                'messagesAsOriginThread',
                'messagesAsOriginThreadIsNeedaction',
            ],
        }),
        /**
         * Not a real field, used to trigger `_onChangeFollowersPartner` when one of
         * the dependencies changes.
         */
        onChangeFollowersPartner: attr({
            compute: '_onChangeFollowersPartner',
            dependencies: [
                'followersPartner',
            ],
        }),
        /**
         * Not a real field, used to trigger `_onChangeLastSeenByCurrentPartnerMessageId` when one of
         * the dependencies changes.
         */
        onChangeLastSeenByCurrentPartnerMessageId: attr({
            compute: '_onChangeLastSeenByCurrentPartnerMessageId',
            dependencies: [
                'lastSeenByCurrentPartnerMessageId',
            ],
        }),
        /**
         * Not a real field, used to trigger `_onChangeThreadViews` when one of
         * the dependencies changes.
         */
        onChangeThreadView: attr({
            compute: '_onChangeThreadViews',
            dependencies: [
                'threadViews',
            ],
        }),
        /**
         * Not a real field, used to trigger `_onIsServerPinnedChanged` when one of
         * the dependencies changes.
         */
        onIsServerPinnedChanged: attr({
            compute: '_onIsServerPinnedChanged',
            dependencies: [
                'isServerPinned',
            ],
        }),
        /**
         * Not a real field, used to trigger `_onServerFoldStateChanged` when one of
         * the dependencies changes.
         */
        onServerFoldStateChanged: attr({
            compute: '_onServerFoldStateChanged',
            dependencies: [
                'serverFoldState',
            ],
        }),
        /**
         * All messages ordered like they are displayed.
         */
        orderedMessages: many2many('mail.message', {
            compute: '_computeOrderedMessages',
            dependencies: ['messages'],
        }),
        /**
         * Serves as compute dependency. (task-2261221)
         */
        orderedMessagesIsTransient: attr({
            related: 'orderedMessages.isTransient',
        }),
        /**
         * All messages ordered like they are displayed. This field does not
         * contain transient messages which are not "real" records.
         */
        orderedNonTransientMessages: many2many('mail.message', {
            compute: '_computeOrderedNonTransientMessages',
            dependencies: [
                'orderedMessages',
                'orderedMessagesIsTransient',
            ],
        }),
        /**
         * Ordered typing members on this thread, excluding the current partner.
         */
        orderedOtherTypingMembers: many2many('mail.partner', {
            compute: '_computeOrderedOtherTypingMembers',
            dependencies: ['orderedTypingMembers'],
        }),
        /**
         * Ordered typing members on this thread. Lower index means this member
         * is currently typing for the longest time. This list includes current
         * partner as typer.
         */
        orderedTypingMembers: many2many('mail.partner', {
            compute: '_computeOrderedTypingMembers',
            dependencies: [
                'orderedTypingMemberLocalIds',
                'typingMembers',
            ],
        }),
        /**
         * Technical attribute to manage ordered list of typing members.
         */
        orderedTypingMemberLocalIds: attr({
            default: [],
        }),
        originThreadAttachments: one2many('mail.attachment', {
            inverse: 'originThread',
        }),
        /**
         * States the `mail.activity` that belongs to `this` and that are
         * overdue (due earlier than today).
         */
        overdueActivities: one2many('mail.activity', {
            compute: '_computeOverdueActivities',
            dependencies: ['activitiesState'],
        }),
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
         * Last message id considered by the server.
         *
         * Useful to compute localMessageUnreadCounter field.
         *
         * @see localMessageUnreadCounter
         */
        serverLastMessageId: attr({
            default: 0,
        }),
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
            dependencies: ['activitiesState'],
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
            dependencies: ['orderedOtherTypingMembers'],
        }),
        /**
         * URL to access to the conversation.
         */
        url: attr({
            compute: '_computeUrl',
            default: '',
            dependencies: [
                'id',
                'model',
            ]
        }),
        uuid: attr(),
    };

    Thread.modelName = 'mail.thread';

    return Thread;
}

registerNewModel('mail.thread', factory);

});
