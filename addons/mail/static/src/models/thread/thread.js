odoo.define('mail/static/src/models/thread/thread.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { clear } = require('mail/static/src/model/model_field_command.js');
const { attr, many2many, many2one, one2many, one2one } = require('mail/static/src/model/model_field_utils.js');
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
                    __mfield_lastCurrentPartnerMessageSeenByEveryone: localThread._computeLastCurrentPartnerMessageSeenByEveryone(),
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
                __mfield_messagesAsServerChannel: [],
            };
            if ('model' in data) {
                data2.__mfield_model = data.model;
            }
            if ('channel_type' in data) {
                data2.__mfield_channel_type = data.channel_type;
                data2.__mfield_model = 'mail.channel';
            }
            if ('create_uid' in data) {
                data2.__mfield_creator = [['insert', {
                    __mfield_id: data.create_uid,
                }]];
            }
            if ('custom_channel_name' in data) {
                data2.__mfield_custom_channel_name = data.custom_channel_name;
            }
            if ('group_based_subscription' in data) {
                data2.__mfield_group_based_subscription = data.group_based_subscription;
            }
            if ('id' in data) {
                data2.__mfield_id = data.id;
            }
            if ('is_minimized' in data && 'state' in data) {
                data2.__mfield_serverFoldState = data.is_minimized ? data.state : 'closed';
            }
            if ('is_moderator' in data) {
                data2.__mfield_is_moderator = data.is_moderator;
            }
            if ('is_pinned' in data) {
                data2.__mfield_isServerPinned = data.is_pinned;
                // FIXME: The following is admittedly odd.
                // Fixing it should entail a deeper reflexion on the group_based_subscription
                // and is_pinned functionalities, especially in python.
                // task-2284357
                if ('group_based_subscription' in data && data.group_based_subscription) {
                    data2.__mfield_isServerPinned = true;
                }
            }
            if ('last_message' in data && data.last_message) {
                data2.__mfield_messagesAsServerChannel.push(['insert', {
                    __mfield_id: data.last_message.id,
                }]);
                data2.__mfield_serverLastMessageId = data.last_message.id;
            }
            if ('last_message_id' in data && data.last_message_id) {
                data2.__mfield_messagesAsServerChannel.push(['insert', {
                    __mfield_id: data.last_message_id,
                }]);
                data2.__mfield_serverLastMessageId = data.last_message_id;
            }
            if ('mass_mailing' in data) {
                data2.__mfield_mass_mailing = data.mass_mailing;
            }
            if ('moderation' in data) {
                data2.__mfield_moderation = data.moderation;
            }
            if ('message_needaction_counter' in data) {
                data2.__mfield_message_needaction_counter = data.message_needaction_counter;
            }
            if ('message_unread_counter' in data) {
                data2.__mfield_serverMessageUnreadCounter = data.message_unread_counter;
            }
            if ('name' in data) {
                data2.__mfield_name = data.name;
            }
            if ('public' in data) {
                data2.__mfield_public = data.public;
            }
            if ('seen_message_id' in data) {
                data2.__mfield_lastSeenByCurrentPartnerMessageId = data.seen_message_id;
            }
            if ('uuid' in data) {
                data2.__mfield_uuid = data.uuid;
            }

            // relations
            if ('members' in data) {
                if (!data.members) {
                    data2.__mfield_members = [['unlink-all']];
                } else {
                    data2.__mfield_members = [
                        ['insert-and-replace', data.members.map(memberData =>
                            this.env.models['mail.partner'].convertData(memberData)
                        )],
                    ];
                }
            }
            if ('seen_partners_info' in data) {
                if (!data.seen_partners_info) {
                    data2.__mfield_partnerSeenInfos = [['unlink-all']];
                } else {
                    /*
                     * FIXME: not optimal to write on relation given the fact that the relation
                     * will be (re)computed based on given fields.
                     * (here channelId will compute partnerSeenInfo.thread))
                     * task-2336946
                     */
                    data2.__mfield_partnerSeenInfos = [
                        ['insert-and-replace',
                            data.seen_partners_info.map(
                                ({ fetched_message_id, partner_id, seen_message_id }) => {
                                    return {
                                        __mfield_channelId: data2.id,
                                        __mfield_lastFetchedMessage: [
                                            fetched_message_id ?
                                            ['insert', {
                                                __mfield_id: fetched_message_id,
                                            }] :
                                            ['unlink-all']],
                                        __mfield_lastSeenMessage: [
                                            seen_message_id ?
                                            ['insert', {
                                                __mfield_id: seen_message_id,
                                            }] :
                                            ['unlink-all']],
                                        __mfield_partnerId: partner_id,
                                    };
                                }
                            ),
                        ]
                    ];
                    if (data.id) {
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
                            data2.__mfield_messageSeenIndicators = [
                                ['insert',
                                    [...messageIds].map(messageId => {
                                       return {
                                           __mfield_channelId: data.id,
                                           __mfield_messageId: messageId,
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
                if (thread.__mfield_model() === 'mail.channel') {
                    return list.concat(thread.__mfield_id());
                }
                return list;
            }, []);
            const channelPreviews = await this.env.services.rpc({
                model: 'mail.channel',
                method: 'channel_fetch_preview',
                args: [channelIds],
            }, { shadow: true });
            this.env.models['mail.message']
                .insert(channelPreviews.filter(p => p.last_message)
                .map(channelPreview =>
                    this.env.models['mail.message'].convertData(channelPreview.last_message)
                )
            );
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
            });
            const channels = this.env.models['mail.thread'].insert(
                channelInfos.map(channelInfo => this.env.models['mail.thread'].convertData(channelInfo))
            );
            // manually force recompute of counter
            this.env.messaging.__mfield_messagingMenu().update();
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
         * Performs the `channel_create` RPC on `mail.channel`.
         *
         * @static
         * @param {Object} param0
         * @param {string} param0.name
         * @param {string} [param0.privacy]
         * @returns {mail.thread} the created channel
         */
        static async performRpcCreateChannel({ name, privacy }) {
            const device = this.env.messaging.__mfield_device();
            const data = await this.env.services.rpc({
                model: 'mail.channel',
                method: 'channel_create',
                args: [name, privacy],
                kwargs: {
                    context: Object.assign({}, this.env.session.user_content, {
                        // optimize the return value by avoiding useless queries
                        // in non-mobile devices
                        isMobile: device.__mfield_isMobile(),
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
            const device = this.env.messaging.__mfield_device();
            // TODO FIX: potential duplicate chat task-2276490
            const data = await this.env.services.rpc({
                model: 'mail.channel',
                method: 'channel_get',
                kwargs: {
                    context: Object.assign({}, this.env.session.user_content, {
                        // optimize the return value by avoiding useless queries
                        // in non-mobile devices
                        isMobile: device.__mfield_isMobile(),
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
            const device = this.env.messaging.__mfield_device();
            const data = await this.env.services.rpc({
                model: 'mail.channel',
                method: 'channel_join_and_get_info',
                args: [[channelId]],
                kwargs: {
                    context: Object.assign({}, this.env.session.user_content, {
                        // optimize the return value by avoiding useless queries
                        // in non-mobile devices
                        isMobile: device.__mfield_isMobile(),
                    }),
                },
            });
            return this.env.models['mail.thread'].insert(
                this.env.models['mail.thread'].convertData(data)
            );
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
            });
            for (const id in data) {
                const recipientInfoList = data[id].map(recipientInfoData => {
                    const [partner_id, emailInfo, reason] = recipientInfoData;
                    const [name, email] = emailInfo && mailUtils.parseEmail(emailInfo);
                    return {
                        __mfield_email: email,
                        __mfield_name: name,
                        __mfield_partner: [
                            partner_id
                                ? ['insert', { __mfield_id: partner_id }]
                                : ['unlink']
                        ],
                        __mfield_reason: reason,
                    };
                });
                this.insert({
                    __mfield_id: parseInt(id),
                    __mfield_model: model,
                    __mfield_suggestedRecipientInfoList: [['insert-and-replace', recipientInfoList]],
                });
            }
        }

        /**
         * @param {string} [stringifiedDomain='[]']
         * @returns {mail.thread_cache}
         */
        cache(stringifiedDomain = '[]') {
            let cache = this.__mfield_caches(this).find(cache =>
                cache.__mfield_stringifiedDomain(this) === stringifiedDomain
            );
            if (!cache) {
                cache = this.env.models['mail.thread_cache'].create({
                    __mfield_stringifiedDomain: stringifiedDomain,
                    __mfield_thread: [['link', this]],
                });
            }
            return cache;
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
                    ['res_id', '=', this.__mfield_id(this)],
                    ['res_model', '=', this.__mfield_model(this)],
                ],
                fields: ['id', 'name', 'mimetype'],
                orderBy: [{ name: 'id', asc: false }],
            }));
            this.update({
                __mfield_originThreadAttachments: [['insert-and-replace',
                    attachmentsData.map(data =>
                        this.env.models['mail.attachment'].convertData(data)
                    )
                ]],
            });
            this.update({
                __mfield_areAttachmentsLoaded: true,
            });
        }

        /**
         * Fetches suggested recipients.
         */
        async fetchAndUpdateSuggestedRecipients() {
            if (this.__mfield_isTemporary(this)) {
                return;
            }
            return this.env.models['mail.thread'].performRpcMailGetSuggestedRecipients({
                model: this.__mfield_model(this),
                res_ids: [this.__mfield_id(this)],
            });
        }

        /**
         * Add current user to provided thread's followers.
         */
        async follow() {
            await this.async(() => this.env.services.rpc({
                model: this.__mfield_model(this),
                method: 'message_subscribe',
                args: [[this.__mfield_id(this)]],
                kwargs: {
                    partner_ids: [this.env.messaging.__mfield_currentPartner(this).__mfield_id(this)],
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
            this.__mfield_mainCache(this).loadNewMessages();
        }

        /**
         * Mark the specified conversation as fetched.
         */
        async markAsFetched() {
            await this.async(() => this.env.services.rpc({
                model: 'mail.channel',
                method: 'channel_fetched',
                args: [[this.__mfield_id(this)]],
            }, { shadow: true }));
        }

        /**
         * Mark the specified conversation as read/seen.
         *
         * @param {integer} messageId the message to be considered as last seen
         */
        async markAsSeen(messageId) {
            if (this.__mfield_model(this) !== 'mail.channel') {
                return;
            }
            if (this.__mfield_pendingSeenMessageId(this) && messageId <= this.__mfield_pendingSeenMessageId(this)) {
                return;
            }
            if (
                this.__mfield_lastSeenByCurrentPartnerMessageId(this) &&
                messageId <= this.__mfield_lastSeenByCurrentPartnerMessageId(this)
            ) {
                return;
            }
            this.update({ __mfield_pendingSeenMessageId: messageId });
            return this.env.models['mail.thread'].performRpcChannelSeen({
                ids: [this.__mfield_id(this)],
                // commands have fake message id that is not integer
                lastMessageId: Math.floor(messageId),
            });
        }

        /**
         * Mark all needaction messages of this thread as read.
         */
        async markNeedactionMessagesAsRead() {
            await this.async(() =>
                this.env.models['mail.message'].markAsRead(this.__mfield_needactionMessages(this))
            );
        }

        /**
         * Notifies the server of new fold state. Useful for initial,
         * cross-tab, and cross-device chat window state synchronization.
         *
         * @param {string} state
         */
        async notifyFoldStateToServer(state) {
            if (this.__mfield_model(this) !== 'mail.channel') {
                // Server sync of fold state is only supported for channels.
                return;
            }
            if (!this.__mfield_uuid(this)) {
                return;
            }
            return this.env.models['mail.thread'].performRpcChannelFold(this.__mfield_uuid(this), state);
        }

        /**
         * Notify server to leave the current channel. Useful for cross-tab
         * and cross-device chat window state synchronization.
         *
         * Only makes sense if isPendingPinned is set to the desired value.
         */
        notifyPinStateToServer() {
            // method is called from _updateAfter so it cannot be async
            if (this.__mfield_isPendingPinned(this)) {
                this.env.services.rpc({
                    model: 'mail.channel',
                    method: 'channel_pin',
                    kwargs: {
                        uuid: this.__mfield_uuid(this),
                        pinned: true,
                    },
                }, { shadow: true });
            } else {
                this.env.services.rpc({
                    model: 'mail.channel',
                    method: 'execute_command',
                    args: [[this.__mfield_id(this)], 'leave']
                }, { shadow: true });
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
            const discuss = this.env.messaging.__mfield_discuss(this);
            // check if thread must be opened in form view
            if (!['mail.box', 'mail.channel'].includes(this.__mfield_model(this))) {
                if (expanded || discuss.__mfield_isOpen(this)) {
                    // Close chat window because having the same thread opened
                    // both in chat window and as main document does not look
                    // good.
                    this.env.messaging.__mfield_chatWindowManager(this).closeThread(this);
                    return this.env.messaging.openDocument({
                        id: this.__mfield_id(this),
                        model: this.__mfield_model(this),
                    });
                }
            }
            // check if thread must be opened in discuss
            const device = this.env.messaging.__mfield_device(this);
            if (
                (!device.__mfield_isMobile(this) && (discuss.__mfield_isOpen(this) || expanded)) ||
                this.__mfield_model(this) === 'mail.box'
            ) {
                return discuss.openThread(this);
            }
            // thread must be opened in chat window
            return this.env.messaging.__mfield_chatWindowManager(this).openThread(this, {
                makeActive: true,
            });
        }

        /**
         * Opens the most appropriate view that is a profile for this thread.
         */
        async openProfile() {
            return this.env.messaging.openDocument({
                id: this.__mfield_id(this),
                model: this.__mfield_model(this),
            });
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

        /**
         * Refresh followers information from server.
         */
        async refreshFollowers() {
            if (this.__mfield_isTemporary(this)) {
                this.update({
                    __mfield_followers: [['unlink-all']],
                });
                return;
            }
            const { followers } = await this.async(() => this.env.services.rpc({
                route: '/mail/read_followers',
                params: {
                    res_id: this.__mfield_id(this),
                    res_model: this.__mfield_model(this),
                },
            }));
            if (followers.length > 0) {
                this.update({
                    __mfield_followers: [['insert-and-replace', followers.map(data =>
                        this.env.models['mail.follower'].convertData(data))
                    ]],
                });
            } else {
                this.update({
                    __mfield_followers: [['unlink-all']],
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
            const currentPartner = this.env.messaging.__mfield_currentPartner(this);
            const newOrderedTypingMemberLocalIds = this.__mfield_orderedTypingMemberLocalIds(this)
                .filter(localId => localId !== currentPartner.localId);
            newOrderedTypingMemberLocalIds.push(currentPartner.localId);
            this.update({
                __mfield_orderedTypingMemberLocalIds: newOrderedTypingMemberLocalIds,
                __mfield_typingMembers: [['link', currentPartner]],
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
            const newOrderedTypingMemberLocalIds = this.__mfield_orderedTypingMemberLocalIds(this)
                .filter(localId => localId !== partner.localId);
            newOrderedTypingMemberLocalIds.push(partner.localId);
            this.update({
                __mfield_orderedTypingMemberLocalIds: newOrderedTypingMemberLocalIds,
                __mfield_typingMembers: [['link', partner]],
            });
        }

        /**
         * Rename the given thread with provided new name.
         *
         * @param {string} newName
         */
        async rename(newName) {
            if (this.__mfield_channel_type(this) === 'chat') {
                await this.async(() => this.env.services.rpc({
                    model: 'mail.channel',
                    method: 'channel_set_custom_name',
                    args: [this.__mfield_id(this)],
                    kwargs: {
                        name: newName,
                    },
                }));
            }
            this.update({
                __mfield_custom_channel_name: newName,
            });
        }

        /**
         * Unfollow current partner from this thread.
         */
        async unfollow() {
            const currentPartnerFollower = this.__mfield_followers(this).find(
                follower => follower.__mfield_partner(this) === this.env.messaging.__mfield_currentPartner(this)
            );
            await this.async(() => currentPartnerFollower.remove());
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
            const currentPartner = this.env.messaging.__mfield_currentPartner(this);
            const newOrderedTypingMemberLocalIds = this.__mfield_orderedTypingMemberLocalIds(this)
                .filter(localId => localId !== currentPartner.localId);
            this.update({
                __mfield_orderedTypingMemberLocalIds: newOrderedTypingMemberLocalIds,
                __mfield_typingMembers: [['unlink', currentPartner]],
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
            const newOrderedTypingMemberLocalIds = this.__mfield_orderedTypingMemberLocalIds(this)
                .filter(localId => localId !== partner.localId);
            this.update({
                __mfield_orderedTypingMemberLocalIds: newOrderedTypingMemberLocalIds,
                __mfield_typingMembers: [['unlink', partner]],
            });
        }

        /**
         * Unsubscribe current user from provided channel.
         */
        unsubscribe() {
            this.env.messaging.__mfield_chatWindowManager(this).closeThread(this);
            this.update({ __mfield_isPendingPinned: false });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            const {
                __mfield_channel_type,
                __mfield_id,
                __mfield_model,
            } = data;
            let threadModel = __mfield_model;
            if (!threadModel && __mfield_channel_type) {
                threadModel = 'mail.channel';
            }
            return `${this.modelName}_${threadModel}_${__mfield_id}`;
        }

        /**
         * @private
         * @returns {mail.attachment[]}
         */
        _computeAllAttachments() {
            const allAttachments = [...new Set(this.__mfield_originThreadAttachments(this).concat(this.__mfield_attachments(this)))]
                .sort((a1, a2) => {
                    // "uploading" before "uploaded" attachments.
                    if (!a1.__mfield_isTemporary(this) && a2.__mfield_isTemporary(this)) {
                        return 1;
                    }
                    if (a1.__mfield_isTemporary(this) && !a2.__mfield_isTemporary(this)) {
                        return -1;
                    }
                    // "most-recent" before "oldest" attachments.
                    return Math.abs(a2.__mfield_id(this)) - Math.abs(a1.__mfield_id(this));
                });
            return [['replace', allAttachments]];
        }

        /**
         * @private
         * @returns {mail.partner}
         */
        _computeCorrespondent() {
            if (this.__mfield_channel_type(this) === 'channel') {
                return [['unlink']];
            }
            const correspondents = this.__mfield_members(this).filter(partner =>
                partner !== this.env.messaging.__mfield_currentPartner(this)
            );
            if (correspondents.length === 1) {
                // 2 members chat
                return [['link', correspondents[0]]];
            }
            if (this.__mfield_members(this).length === 1) {
                // chat with oneself
                return [['link', this.__mfield_members(this)[0]]];
            }
            return [['unlink']];
        }

        /**
         * @private
         * @returns {string}
         */
        _computeDisplayName() {
            if (
                this.__mfield_channel_type(this) === 'chat' &&
                this.__mfield_correspondent(this)
            ) {
                return (
                    this.__mfield_custom_channel_name(this) ||
                    this.__mfield_correspondent(this).__mfield_nameOrDisplayName(this)
                );
            }
            return this.__mfield_name(this);
        }

        /**
         * @private
         */
        _computeHasSeenIndicators() {
            if (this.__mfield_model(this) !== 'mail.channel') {
                return false;
            }
            if (this.__mfield_mass_mailing(this)) {
                return false;
            }
            return ['chat', 'livechat'].includes(this.__mfield_channel_type(this));
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsChatChannel() {
            return this.__mfield_channel_type(this) === 'chat';
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsCurrentPartnerFollowing() {
            return this.__mfield_followers(this).some(follower =>
                follower.__mfield_partner(this) &&
                follower.__mfield_partner(this) === this.env.messaging.__mfield_currentPartner(this)
            );
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsModeratedByCurrentPartner() {
            if (!this.__mfield_messaging(this)) {
                return false;
            }
            if (!this.__mfield_messaging(this).__mfield_currentPartner(this)) {
                return false;
            }
            return this.__mfield_moderators(this).includes(this.env.messaging.__mfield_currentPartner(this));
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsPinned() {
            return (
                this.__mfield_isPendingPinned(this) !== undefined ?
                this.__mfield_isPendingPinned(this) :
                this.__mfield_isServerPinned(this)
            );
        }

        /**
         * @private
         * @returns {mail.message}
         */
        _computeLastCurrentPartnerMessageSeenByEveryone() {
            if (
                !this.__mfield_partnerSeenInfos(this) ||
                !this.__mfield_orderedMessages(this)
            ) {
                return [['unlink-all']];
            }
            const otherPartnerSeenInfos =
                this.__mfield_partnerSeenInfos(this).filter(partnerSeenInfo =>
                    partnerSeenInfo.__mfield_partner(this) !== this.__mfield_messagingCurrentPartner(this)
                );
            if (otherPartnerSeenInfos.length === 0) {
                return [['unlink-all']];
            }

            const otherPartnersLastSeenMessageIds =
                otherPartnerSeenInfos.map(partnerSeenInfo =>
                    partnerSeenInfo.__mfield_lastSeenMessage(this) ?
                    partnerSeenInfo.__mfield_lastSeenMessage(this).__mfield_id(this) :
                    0
                );
            if (otherPartnersLastSeenMessageIds.length === 0) {
                return [['unlink-all']];
            }
            const lastMessageSeenByAllId = Math.min(
                ...otherPartnersLastSeenMessageIds
            );
            const currentPartnerOrderedSeenMessages =
                this.__mfield_orderedMessages(this).filter(message =>
                    message.__mfield_author(this) === this.__mfield_messagingCurrentPartner(this) &&
                    message.__mfield_id(this) <= lastMessageSeenByAllId);

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
            } = this.__mfield_orderedMessages(this);
            if (lastMessage) {
                return [['link', lastMessage]];
            }
            return [['unlink']];
        }

        /**
         * @private
         * @returns {mail.message|undefined}
         */
        _computeLastNeedactionMessage() {
            const orderedNeedactionMessages = this.__mfield_needactionMessages(this).sort(
                (m1, m2) => m1.__mfield_id(this) < m2.__mfield_id(this) ? -1 : 1
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
            // the only situations where serverMessageUnreadCounter can/have to be
            // trusted are:
            // - we have no last message (and then no messages at all)
            // - the message it used to compute is the last message we know
            if (this.__mfield_orderedMessages(this).length === 0) {
                return this.__mfield_serverMessageUnreadCounter(this);
            }
            // from here serverLastMessageId is not undefined because
            // orderedMessages contain at least one message.
            if (!this.__mfield_lastSeenByCurrentPartnerMessageId(this)) {
                return this.__mfield_serverMessageUnreadCounter(this);
            }
            const firstMessage = this.__mfield_orderedMessages(this)[0];
            // if the lastSeenByCurrentPartnerMessageId is not known (not fetched), then we
            // need to rely on server value to determine the amount of unread
            // messages until the last message it knew when computing the
            // serverMessageUnreadCounter
            if (this.__mfield_lastSeenByCurrentPartnerMessageId(this) < firstMessage.__mfield_id(this)) {
                const fetchedNotSeenMessages = this.__mfield_orderedMessages(this).filter(message =>
                    message.__mfield_id(this) > this.__mfield_serverLastMessageId(this)
                );
                return this.__mfield_serverMessageUnreadCounter(this) + fetchedNotSeenMessages.length;
            }
            // lastSeenByCurrentPartnerMessageId is a known message,
            // then we can forget serverMessageUnreadCounter
            const maxId = Math.max(
                this.__mfield_serverLastMessageId(this),
                this.__mfield_lastSeenByCurrentPartnerMessageId(this)
            );
            return this.__mfield_orderedMessages(this).reduce(
                (acc, message) => acc + (message.__mfield_id(this) > maxId ? 1 : 0),
                0
            );
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
            return [['replace', this.__mfield_messages(this).filter(message => message.__mfield_isNeedaction(this))]];
        }

        /**
         * @private
         * @returns {mail.message[]}
         */
        _computeOrderedMessages() {
            return [['replace', this.__mfield_messages(this).sort((m1, m2) =>
                m1.__mfield_id(this) < m2.__mfield_id(this) ? -1 : 1
            )]];
        }

        /**
         * @private
         * @returns {mail.partner[]}
         */
        _computeOrderedOtherTypingMembers() {
            return [[
                'replace',
                this.__mfield_orderedTypingMembers(this).filter(
                    member => member !== this.env.messaging.__mfield_currentPartner(this)
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
                this.__mfield_orderedTypingMemberLocalIds(this)
                    .map(localId => this.env.models['mail.partner'].get(localId))
                    .filter(member => !!member),
            ]];
        }

        /**
         * @private
         * @returns {string}
         */
        _computeTypingStatusText() {
            if (this.__mfield_orderedOtherTypingMembers(this).length === 0) {
                return this.constructor.fields.__mfield_typingStatusText.default;
            }
            if (this.__mfield_orderedOtherTypingMembers(this).length === 1) {
                return _.str.sprintf(
                    this.env._t("%s is typing..."),
                    this.__mfield_orderedOtherTypingMembers(this)[0].__mfield_nameOrDisplayName(this)
                );
            }
            if (this.__mfield_orderedOtherTypingMembers(this).length === 2) {
                return _.str.sprintf(
                    this.env._t("%s and %s are typing..."),
                    this.__mfield_orderedOtherTypingMembers(this)[0].__mfield_nameOrDisplayName(this),
                    this.__mfield_orderedOtherTypingMembers(this)[1].__mfield_nameOrDisplayName(this)
                );
            }
            return _.str.sprintf(
                this.env._t("%s, %s and more are typing..."),
                this.__mfield_orderedOtherTypingMembers(this)[0].__mfield_nameOrDisplayName(this),
                this.__mfield_orderedOtherTypingMembers(this)[1].__mfield_nameOrDisplayName(this)
            );
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
                if (this.__mfield_model(this) === 'mail.channel') {
                    await this.async(() => this.env.services.rpc({
                        model: 'mail.channel',
                        method: 'notify_typing',
                        args: [this.__mfield_id(this)],
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
         * Handles change of fold state coming from the server. Useful to
         * synchronize corresponding chat window.
         *
         * @private
         */
        _onServerFoldStateChanged() {
            if (!this.env.messaging.__mfield_chatWindowManager(this)) {
                // avoid crash during destroy
                return;
            }
            if (this.__mfield_serverFoldState(this) === 'closed') {
                this.env.messaging.__mfield_chatWindowManager(this).closeThread(this, {
                    notifyServer: false,
                });
            } else {
                this.env.messaging.__mfield_chatWindowManager(this).openThread(this, {
                    isFolded: this.__mfield_serverFoldState(this) === 'folded',
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
            const action = {
                type: 'ir.actions.act_window',
                res_model: 'mail.wizard.invite',
                view_mode: 'form',
                views: [[false, 'form']],
                name: this.env._t("Invite Follower"),
                target: 'new',
                context: {
                    default_res_model: this.__mfield_model(this),
                    default_res_id: this.__mfield_id(this),
                    mail_invite_follower_channel_only,
                },
            };
            this.env.bus.trigger('do-action', {
                action,
                options: {
                    on_close: () => this.refreshFollowers(),
                },
            });
        }

        /**
         * @override
         */
        _updateAfter(previous) {
            if (this.__mfield_model(this) !== 'mail.channel') {
                // pin state only makes sense on channels
                return;
            }
            if (
                this.__mfield_isPendingPinned(this) !== undefined &&
                previous.isPendingPinned !== this.__mfield_isPendingPinned(this)
            ) {
                this.notifyPinStateToServer();
            }
            if (this.__mfield_isServerPinned(this) === this.__mfield_isPendingPinned(this)) {
                this.update({ __mfield_isPendingPinned: clear() });
            }
        }

        /**
         * @override
         */
        _updateBefore() {
            return {
                isPendingPinned: this.__mfield_isPendingPinned(this),
            };
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
            if (!this.__mfield_typingMembers(this).includes(partner)) {
                this._otherMembersLongTypingTimers.delete(partner);
                return;
            }
            this.unregisterOtherMemberTypingMember(partner);
        }

    }

    Thread.fields = {
        __mfield_allAttachments: many2many('mail.attachment', {
            compute: '_computeAllAttachments',
            dependencies: [
                '__mfield_attachments',
                '__mfield_originThreadAttachments',
            ],
        }),
        __mfield_areAttachmentsLoaded: attr({
            default: false,
        }),
        __mfield_attachments: many2many('mail.attachment', {
            inverse: '__mfield_threads',
        }),
        __mfield_caches: one2many('mail.thread_cache', {
            inverse: '__mfield_thread',
            isCausal: true,
        }),
        __mfield_channel_type: attr(),
        /**
         * States the `mail.chat_window` related to `this`. Serves as compute
         * dependency. It is computed from the inverse relation and it should
         * otherwise be considered read-only.
         */
        __mfield_chatWindow: one2one('mail.chat_window', {
            inverse: '__mfield_thread',
        }),
        /**
         * Serves as compute dependency.
         */
        __mfield_chatWindowIsFolded: attr({
            related: '__mfield_chatWindow.__mfield_isFolded',
        }),
        __mfield_composer: one2one('mail.composer', {
            default: [['create']],
            inverse: '__mfield_thread',
            isCausal: true,
        }),
        __mfield_correspondent: many2one('mail.partner', {
            compute: '_computeCorrespondent',
            dependencies: [
                '__mfield_channel_type',
                '__mfield_members',
                '__mfield_messagingCurrentPartner',
            ],
            inverse: '__mfield_correspondentThreads',
        }),
        __mfield_correspondentNameOrDisplayName: attr({
            related: '__mfield_correspondent.__mfield_nameOrDisplayName',
        }),
        __mfield_counter: attr({
            default: 0,
        }),
        __mfield_creator: many2one('mail.user'),
        __mfield_custom_channel_name: attr(),
        __mfield_displayName: attr({
            compute: '_computeDisplayName',
            dependencies: [
                '__mfield_channel_type',
                '__mfield_correspondent',
                '__mfield_correspondentNameOrDisplayName',
                '__mfield_custom_channel_name',
                '__mfield_name',
            ],
        }),
        __mfield_followersPartner: many2many('mail.partner', {
            related: '__mfield_followers.__mfield_partner',
        }),
        __mfield_followers: one2many('mail.follower', {
            inverse: '__mfield_followedThread',
        }),
        __mfield_group_based_subscription: attr({
            default: false,
        }),
        /**
         * Determine whether this thread has the seen indicators (V and VV)
         * enabled or not.
         */
        __mfield_hasSeenIndicators: attr({
            compute: '_computeHasSeenIndicators',
            default: false,
            dependencies: [
                '__mfield_channel_type',
                '__mfield_mass_mailing',
                '__mfield_model',
            ],
        }),
        __mfield_id: attr(),
        /**
         * States whether this thread is a `mail.channel` qualified as chat.
         *
         * Useful to list chat channels, like in messaging menu with the filter
         * 'chat'.
         */
        __mfield_isChatChannel: attr({
            compute: '_computeIsChatChannel',
            dependencies: [
                '__mfield_channel_type',
            ],
            default: false,
        }),
        __mfield_isCurrentPartnerFollowing: attr({
            compute: '_computeIsCurrentPartnerFollowing',
            default: false,
            dependencies: [
                '__mfield_followersPartner',
                '__mfield_messagingCurrentPartner',
            ],
        }),
        __mfield_isModeratedByCurrentPartner: attr({
            compute: '_computeIsModeratedByCurrentPartner',
            dependencies: [
                '__mfield_messagingCurrentPartner',
                '__mfield_moderators',
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
        __mfield_isPendingPinned: attr(),
        /**
         * Boolean that determines whether this thread is pinned
         * in discuss and present in the messaging menu.
         */
        __mfield_isPinned: attr({
            compute: '_computeIsPinned',
            dependencies: [
                '__mfield_isPendingPinned',
                '__mfield_isServerPinned',
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
        __mfield_isServerPinned: attr({
            default: false,
        }),
        __mfield_isTemporary: attr({
            default: false,
        }),
        __mfield_is_moderator: attr({
            default: false,
        }),
        __mfield_lastCurrentPartnerMessageSeenByEveryone: many2one('mail.message', {
            compute: '_computeLastCurrentPartnerMessageSeenByEveryone',
            dependencies: [
                '__mfield_partnerSeenInfos',
                '__mfield_orderedMessages',
                '__mfield_messagingCurrentPartner',
            ],
        }),
        __mfield_lastMessage: many2one('mail.message', {
            compute: '_computeLastMessage',
            dependencies: [
                '__mfield_orderedMessages',
            ],
        }),
        __mfield_lastNeedactionMessage: many2one('mail.message', {
            compute: '_computeLastNeedactionMessage',
            dependencies: [
                '__mfield_needactionMessages',
            ],
        }),
        /**
         * Last seen message id of the channel by current partner.
         *
         * If there is a pending seen message id change, it is immediately applied
         * on the interface to avoid a feeling of unresponsiveness. Otherwise the
         * last known message id of the server is used.
         *
         * Also, it needs to be kept as an id because it's considered like a "date" and could stay
         * even if corresponding message is deleted. It is basically used to know which
         * messages are before or after it.
         */
        __mfield_lastSeenByCurrentPartnerMessageId: attr(),
        /**
         * Local value of message unread counter, that means it is based on initial server value and
         * updated with interface updates.
         */
        __mfield_localMessageUnreadCounter: attr({
            compute: '_computeLocalMessageUnreadCounter',
            dependencies: [
                '__mfield_lastMessage',
                '__mfield_lastSeenByCurrentPartnerMessageId',
                '__mfield_orderedMessages',
                '__mfield_serverLastMessageId',
                '__mfield_serverMessageUnreadCounter',
            ],
        }),
        __mfield_mainCache: one2one('mail.thread_cache', {
            compute: '_computeMainCache',
        }),
        __mfield_mass_mailing: attr({
            default: false,
        }),
        __mfield_members: many2many('mail.partner', {
            inverse: '__mfield_memberThreads',
        }),
        __mfield_message_needaction_counter: attr({
            default: 0,
        }),
        /**
         * All messages that this thread is linked to.
         * Note that this field is automatically computed by inverse
         * computed field. This field is readonly.
         */
        __mfield_messages: many2many('mail.message', {
            inverse: '__mfield_threads',
        }),
        /**
         * All messages that are contained on this channel on the server.
         * Equivalent to the inverse of python field `channel_ids`.
         */
        __mfield_messagesAsServerChannel: many2many('mail.message', {
            inverse: '__mfield_serverChannels',
        }),
        __mfield_messageSeenIndicators: one2many('mail.message_seen_indicator', {
            inverse: '__mfield_thread',
            isCausal: true,
        }),
        __mfield_messaging: many2one('mail.messaging', {
            compute: '_computeMessaging',
        }),
        __mfield_messagingCurrentPartner: many2one('mail.partner', {
            related: '__mfield_messaging.__mfield_currentPartner',
        }),
        __mfield_model: attr(),
        __mfield_model_name: attr(),
        __mfield_moderation: attr({
            default: false,
        }),
        /**
         * Partners that are moderating this thread (only applies to channels).
         */
        __mfield_moderators: many2many('mail.partner', {
            inverse: '__mfield_moderatedChannels',
        }),
        __mfield_moduleIcon: attr(),
        __mfield_name: attr(),
        __mfield_needactionMessages: many2many('mail.message', {
            compute: '_computeNeedactionMessages',
            dependencies: [
                '__mfield_messages',
            ],
        }),
        /**
         * Not a real field, used to trigger `_onServerFoldStateChanged` when one of
         * the dependencies changes.
         */
        __mfield_onServerFoldStateChanged: attr({
            compute: '_onServerFoldStateChanged',
            dependencies: [
                '__mfield_serverFoldState',
            ],
        }),
        __mfield_orderedMessages: many2many('mail.message', {
            compute: '_computeOrderedMessages',
            dependencies: [
                '__mfield_messages',
            ],
        }),
        /**
         * Ordered typing members on this thread, excluding the current partner.
         */
        __mfield_orderedOtherTypingMembers: many2many('mail.partner', {
            compute: '_computeOrderedOtherTypingMembers',
            dependencies: [
                '__mfield_orderedTypingMembers',
            ],
        }),
        /**
         * Ordered typing members on this thread. Lower index means this member
         * is currently typing for the longest time. This list includes current
         * partner as typer.
         */
        __mfield_orderedTypingMembers: many2many('mail.partner', {
            compute: '_computeOrderedTypingMembers',
            dependencies: [
                '__mfield_orderedTypingMemberLocalIds',
                '__mfield_typingMembers',
            ],
        }),
        /**
         * Technical attribute to manage ordered list of typing members.
         */
        __mfield_orderedTypingMemberLocalIds: attr({
            default: [],
        }),
        __mfield_originThreadAttachments: one2many('mail.attachment', {
            inverse: '__mfield_originThread',
        }),
        __mfield_partnerSeenInfos: one2many('mail.thread_partner_seen_info', {
            inverse: '__mfield_thread',
            isCausal: true,
        }),
        /**
         * Determine if there is a pending seen message change, which is a change
         * of seen message requested by the client but not yet confirmed by the
         * server.
         */
        __mfield_pendingSeenMessageId: attr(),
        __mfield_public: attr(),
        /**
         * Determine the last fold state known by the server, which is the fold
         * state displayed after initialization or when the last pending
         * fold state change was confirmed by the server.
         *
         * This field should be considered read only in most situations. Only
         * the code handling fold state change from the server should typically
         * update it.
         */
        __mfield_serverFoldState: attr({
            default: 'closed',
        }),
        /**
         * Last message id considered by the server.
         *
         * Useful to compute localMessageUnreadCounter field.
         *
         * @see __mfield_localMessageUnreadCounter
         */
        __mfield_serverLastMessageId: attr({
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
         * @see __mfield_localMessageUnreadCounter
         */
        __mfield_serverMessageUnreadCounter: attr({
            default: 0,
        }),
        /**
         * Determines the `mail.suggested_recipient_info` concerning `this`.
         */
        __mfield_suggestedRecipientInfoList: one2many('mail.suggested_recipient_info', {
            inverse: '__mfield_thread',
        }),
        /**
         * Members that are currently typing something in the composer of this
         * thread, including current partner.
         */
        __mfield_typingMembers: many2many('mail.partner'),
        /**
         * Text that represents the status on this thread about typing members.
         */
        __mfield_typingStatusText: attr({
            compute: '_computeTypingStatusText',
            default: '',
            dependencies: [
                '__mfield_orderedOtherTypingMembers',
            ],
        }),
        __mfield_uuid: attr(),
        __mfield_threadViews: one2many('mail.thread_view', {
            inverse: '__mfield_thread',
        }),
    };

    Thread.modelName = 'mail.thread';

    return Thread;
}

registerNewModel('mail.thread', factory);

});
