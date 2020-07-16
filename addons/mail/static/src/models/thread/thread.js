odoo.define('mail/static/src/models/thread/thread.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2many, many2one, one2many, one2one } = require('mail/static/src/model/model_field.js');
const throttle = require('mail/static/src/utils/throttle/throttle.js');
const Timer = require('mail/static/src/utils/timer/timer.js');

function factory(dependencies) {

    class Thread extends dependencies['mail.model'] {

        /**
         * FIXME With this, whenever client is aware of new thread, this will
         * (almost) always focus its composer when displayed. This shouldn't be
         * the case, instead auto-focus of composer is flow-specific.
         * See task-2277537
         *
         * @override
         */
        static create(data) {
            if (!data.composer) {
                data.composer = [['create', {
                    isDoFocus: true,
                }]];
            }
            return super.create(data);
        }

        /**
         * @override
         */
        init(...args) {
            super.init(...args);
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
        }

        /**
         * @override
         */
        delete(...args) {
            this._currentPartnerInactiveTypingTimer.clear();
            this._currentPartnerLongTypingTimer.clear();
            this._throttleNotifyCurrentPartnerTypingStatus.clear();
            for (const timer of this._otherMembersLongTypingTimers.values()) {
                timer.clear();
            }
            super.delete(...args);
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
            const data2 = {};
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
                // FIXME: The following is admittedly odd.
                // Fixing it should entail a deeper reflexion on the group_based_subscription
                // and is_pinned functionalities, especially in python.
                // task-2284357
                if ('group_based_subscription' in data && data.group_based_subscription) {
                    data2.isServerPinned = true;
                }
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
                data2.message_unread_counter = data.message_unread_counter;
            }
            if ('name' in data) {
                data2.name = data.name;
            }
            if ('public' in data) {
                data2.public = data.public;
            }
            if ('seen_message_id' in data) {
                data2.seen_message_id = data.seen_message_id;
            }
            if ('uuid' in data) {
                data2.uuid = data.uuid;
            }

            // relation
            if ('direct_partner' in data) {
                if (!data.direct_partner) {
                    data2.correspondent = [['unlink-all']];
                } else {
                    data2.correspondent = [
                        ['insert', this.env.models['mail.partner'].convertData(data.direct_partner[0])],
                    ];
                }
            }
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
                    data2.partnerSeenInfos = [
                        ['insert-and-replace',
                            data.seen_partners_info.map(
                                ({ fetched_message_id, id, partner_id, seen_message_id}) => {
                                    return {
                                        id,
                                        lastFetchedMessage: [seen_message_id ? ['insert', {id: seen_message_id}] : ['unlink-all']],
                                        lastSeenMessage: [fetched_message_id ? ['insert', {id: fetched_message_id}] : ['unlink-all']],
                                        partner: [['insert', {id: partner_id}]],
                                    };
                                })
                        ]
                    ];
                    if (data.id || this.id) {
                        const messageIds = data.seen_partners_info.reduce((currentSet, { fetched_message_id, seen_message_id}) => {
                            if (fetched_message_id) {
                                currentSet.add(fetched_message_id);
                            }
                            if (seen_message_id) {
                                currentSet.add(seen_message_id);
                            }
                            return currentSet;
                        }, new Set());
                        if (messageIds.size > 0) {
                            data2.messageSeenIndicators = [
                                ['insert',
                                    [...messageIds].map(messageId => {
                                       return {
                                           id: this.env.models['mail.message_seen_indicator'].computeId(messageId, data.id || this.id),
                                           message: [['insert', {id: messageId}]],
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
         * Create a channel, which is a special kind of thread on model
         * 'mail.channel' with multiple members.
         *
         * @static
         * @param {Object} param0
         * @param {boolean} [param0.autoselect=false] if set, when channel
         *   has been created, it auto-open the channel. This opens in discuss
         *   or chat window, depending on whether discuss is open or not.
         * @param {string} [param0.autoselectChatWindowMode]
         * @param {string} param0.name
         * @param {integer} [param0.partnerId]
         * @param {string} [param0.public]
         * @param {string} param0.type
         */
        static async createChannel({
            autoselect = false,
            autoselectChatWindowMode,
            name,
            partnerId,
            public: publicStatus,
            type,
        }) {
            const device = this.env.messaging.device;
            // TODO FIX: potential duplicate chat task-2276490
            const data = await this.env.services.rpc({
                model: 'mail.channel',
                method: type === 'chat' ? 'channel_get' : 'channel_create',
                args: type === 'chat' ? [[partnerId]] : [name, publicStatus],
                kwargs: {
                    context: Object.assign({}, this.env.session.user_content, {
                        isMobile: device.isMobile,
                    }),
                }
            });
            const thread = this.insert(this.convertData(data));
            if (autoselect) {
                thread.open({ chatWindowMode: autoselectChatWindowMode });
            }
        }

        /**
         * Join a channel. This channel may not yet exists in the store.
         *
         * @static
         * @param {integer} channelId
         * @param {Object} [param1={}]
         * @param {boolean} [param1.autoselect=false]
         */
        static async joinChannel(channelId, { autoselect = false } = {}) {
            let channel = this.find(thread =>
                thread.id === channelId &&
                thread.model === 'mail.channel'
            );
            if (channel && channel.isPinned) {
                return;
            }
            const data = await this.env.services.rpc({
                model: 'mail.channel',
                method: 'channel_join_and_get_info',
                args: [[channelId]]
            });
            // We just joined the channel because of the previous rpc
            // the main assumption here is that we didn't have the channel
            // in memory. If we did though, clear the pending state and
            // let the server's data be the master
            const convertedData = Object.assign(
                { isPendingPinned: undefined },
                this.convertData(data),
            );
            channel = this.insert(convertedData);
            if (autoselect) {
                channel.open({ resetDiscussDomain: true });
            }
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
            const messagePreviews = await this.env.services.rpc({
                model: 'mail.channel',
                method: 'channel_fetch_preview',
                args: [channelIds],
            }, { shadow: true });
            for (const preview of messagePreviews) {
                const messageData = preview.last_message;
                if (messageData) {
                    this.env.models['mail.message'].insert(
                        this.env.models['mail.message'].convertData(messageData)
                    );
                }
            }
        }

        /**
         * @param {string} [stringifiedDomain='[]']
         * @returns {mail.thread_cache}
         */
        cache(stringifiedDomain = '[]') {
            let cache = this.caches.find(cache => cache.stringifiedDomain === stringifiedDomain);
            if (!cache) {
                cache = this.env.models['mail.thread_cache'].create({
                    stringifiedDomain,
                    thread: [['link', this]],
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
                    ['res_id', '=', this.id],
                    ['res_model', '=', this.model],
                ],
                fields: ['id', 'name', 'mimetype'],
                orderBy: [{ name: 'id', asc: false }],
            }));
            for (const attachmentData of attachmentsData) {
                this.env.models['mail.attachment'].insert(Object.assign({
                    originThread: [['link', this]],
                }, this.env.models['mail.attachment'].convertData(attachmentData)));
            }
            this.update({ areAttachmentsLoaded: true });
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
         */
        async markAsSeen() {
            if (this.message_unread_counter === 0) {
                return;
            }
            if (this.model === 'mail.channel') {
                const seen_message_id = await this.async(() => this.env.services.rpc({
                    model: 'mail.channel',
                    method: 'channel_seen',
                    args: [[this.id]]
                }, { shadow: true }));
                this.update({ seen_message_id });
            }
            this.update({ message_unread_counter: 0 });
        }

        /**
         * Mark all needaction messages of this thread as read.
         */
        async markNeedactionMessagesAsRead() {
            await this.async(() =>
                this.env.models['mail.message'].markAsRead(this.needactionMessages)
            );
        }

        /**
         * Notify server the fold state of this thread. Useful for cross-tab
         * and cross-device chat window state synchronization.
         *
         * Only makes sense if pendingFoldState is set to the desired value.
         */
        async notifyFoldStateToServer() {
            await this.async(() => this.env.services.rpc({
                model: 'mail.channel',
                method: 'channel_fold',
                kwargs: {
                    uuid: this.uuid,
                    state: this.pendingFoldState,
                }
            }, { shadow: true }));
        }

        /**
         * Notify server to leave the current channel. Useful for cross-tab
         * and cross-device chat window state synchronization.
         *
         * Only makes sense if pendingServerState is set to 'unpin'.
         */
        async notifyUnPinToServer() {
            return this.async(() => this.env.services.rpc({
                model: 'mail.channel',
                method: 'execute_command',
                args: [[this.id], 'leave']
            }));
        }

        /**
         * Open provided thread, either in discuss app or as a chat window.
         *
         * @param {Object} param0
         * @param {string} [param0.chatWindowMode='last_visible']
         * @param {boolean} [param0.resetDiscussDomain=false]
         */
        open({ chatWindowMode = 'last_visible', resetDiscussDomain = false } = {}) {
            const device = this.env.messaging.device;
            const discuss = this.env.messaging.discuss;
            const messagingMenu = this.env.messaging.messagingMenu;
            if (!['mail.box', 'mail.channel'].includes(this.model)) {
                this.env.messaging.openDocument({
                    id: this.id,
                    model: this.model,
                });
            }
            if (
                (!device.isMobile && discuss.isOpen) ||
                (device.isMobile && this.model === 'mail.box')
            ) {
                if (resetDiscussDomain) {
                    discuss.threadViewer.update({ stringifiedDomain: '[]' });
                }
                discuss.threadViewer.update({ thread: [['link', this]] });
            } else {
                this.env.messaging.chatWindowManager.openThread(this, { mode: chatWindowMode });
            }
            if (!device.isMobile) {
                messagingMenu.close();
            }
        }

        /**
         * Open this thread in an expanded way, that is not in a chat window.
         */
        openExpanded() {
            const discuss = this.env.messaging.discuss;
            if (['mail.channel', 'mail.box'].includes(this.model)) {
                discuss.threadViewer.update({ thread: [['replace', this]] });
                this.env.bus.trigger('do-action', {
                    action: 'mail.action_discuss',
                    options: {
                        clear_breadcrumbs: false,
                        active_id: discuss.threadToActiveId(this),
                        on_reverse_breadcrumb: () => discuss.close(),
                    },
                });
            } else {
                this.env.bus.trigger('do-action', {
                    action: {
                        type: 'ir.actions.act_window',
                        res_model: this.model,
                        views: [[false, 'form']],
                        res_id: this.id,
                    },
                });
            }
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
            // FIXME Do that with only one RPC (see task-2243180)
            const [{ message_follower_ids: followerIds }] = await this.async(() => this.env.services.rpc({
                model: this.model,
                method: 'read',
                args: [this.id, ['message_follower_ids']],
            }));
            if (followerIds && followerIds.length > 0) {
                const { followers } = await this.async(() => this.env.services.rpc({
                    route: '/mail/read_followers',
                    params: {
                        follower_ids: followerIds,
                        context: {}, // FIXME empty context to be overridden in session.js with 'allowed_company_ids' task-2243187
                    }
                }));
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
            this.update({
                pendingFoldState: 'closed',
                isPendingPinned: false,
            });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _findFunctionFromData(data) {
            return record => record.id === data.id && record.model === data.model;
        }

        /**
         * @private
         * @returns {mail.attachment[]}
         */
        _computeAllAttachments() {
            const allAttachments = [...new Set(this.originThreadAttachments.concat(this.attachments))]
                .sort((a1, a2) => a1.id < a2.id ? 1 : -1);
            return [['replace', allAttachments]];
        }

        /**
         * @private
         * @returns {mail.chat_window[]}
         */
        _computeChatWindows() {
            const chatWindowViewers = this.viewers.filter(viewer => !!viewer.chatWindow);
            return [['replace', chatWindowViewers.map(viewer => viewer.chatWindow)]];
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
         * @returns {string}
         */
        _computeFoldState() {
            return this.pendingFoldState || this.serverFoldState;
        }

        /**
         * @private
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
            if (this.model !== 'mail.channel') {
                return false;
            }
            if (!this.messaging) {
                return false;
            }
            if (!this.messaging.currentPartner) {
                return false;
            }
            return this.messaging.currentPartner.moderatedChannelIds.includes(this.id);
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
            if (!this.partnerSeenInfos || !this.orderedMessages) {
                return [['unlink-all']];
            }
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
                this.orderedMessages.filter(message =>
                    message.author === this.messagingCurrentPartner &&
                    message.id <= lastMessageSeenByAllId);

            if (
                !currentPartnerOrderedSeenMessages ||
                currentPartnerOrderedSeenMessages.length === 0
            ) {
                return [['unlink-all']];
            }
            return [['replace', currentPartnerOrderedSeenMessages.slice().pop()]];
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
            return [['replace', lastMessage]];
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
            return [['replace', lastNeedactionMessage]];
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
        _computeOrderedMessages() {
            return [['replace', this.messages.sort((m1, m2) => m1.id < m2.id ? -1 : 1)]];
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
         * @override
         */
        _createRecordLocalId(data) {
            const { channel_type, id, isTemporary = false, model } = data;
            let threadModel = model;
            if (!threadModel && channel_type) {
                threadModel = 'mail.channel';
            }
            const Thread = this.env.models['mail.thread'];
            if (isTemporary) {
                return `${Thread.modelName}_${id}`;
            }
            return `${Thread.modelName}_${threadModel}_${id}`;
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

        /**
         * @override
         */
        _updateAfter(previous) {
            if (this.model !== 'mail.channel') {
                // fold state only makes sense on channels
                return;
            }
            if (
                this.pendingFoldState &&
                previous.pendingFoldState !== this.pendingFoldState
            ) {
                this.notifyFoldStateToServer();
            }
            if (
                this.serverFoldState === this.pendingFoldState
            ) {
                this.update({ pendingFoldState: undefined });
            }
            if (
                this.isPendingPinned === false &&
                previous.isPendingPinned !== this.isPendingPinned
            ) {
                this.notifyUnPinToServer();
            }
            if (
                this.isServerPinned === this.isPendingPinned
            ) {
                this.update({ isPendingPinned: undefined });
            }

            // TODO FIXME prevent to open/close a channel on mobile when you
            // open/close it on desktop (task-2267593)

            // chat window
            if (previous.foldState === this.foldState) {
                // avoid updating chatWindows when not changing foldState
                // important to avoid issues when thread is in progress of being
                // opened, because the foldState is updated only at the end of
                // the process
                return;
            }
            if (this.foldState !== 'closed' && this.chatWindows.length === 0) {
                // condition to avoid crash during destroy
                if (this.env.messaging.chatWindowManager) {
                    this.env.messaging.chatWindowManager.openThread(this);
                }
            }
            if (this.foldState === 'closed' && this.chatWindows.length > 0) {
                for (const chatWindow of this.chatWindows) {
                    chatWindow.close();
                }
            }
        }

        /**
         * @override
         */
        _updateBefore() {
            return {
                foldState: this.foldState,
                isPendingPinned: this.isPendingPinned,
                pendingFoldState: this.pendingFoldState,
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
            if (!this.typingMembers.includes(partner)) {
                this._otherMembersLongTypingTimers.delete(partner);
                return;
            }
            this.unregisterOtherMemberTypingMember(partner);
        }

    }

    Thread.fields = {
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
        attachments: many2many('mail.attachment', {
            inverse: 'threads',
        }),
        caches: one2many('mail.thread_cache', {
            inverse: 'thread',
            isCausal: true,
        }),
        channel_type: attr(),
        chatWindows: one2many('mail.chat_window', {
            compute: '_computeChatWindows',
            dependencies: ['viewersChatWindow'],
        }),
        composer: one2one('mail.composer', {
            inverse: 'thread',
            isCausal: true,
        }),
        correspondent: many2one('mail.partner', {
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
        /**
         * Determine the fold state of the channel on the web client.
         *
         * If there is a pending fold state change, it is immediately applied on
         * the interface to avoid a feeling of unresponsiveness. Otherwise the
         * last known fold state of the server is used.
         *
         * This field must be considered read only.
         */
        foldState: attr({
            compute: '_computeFoldState',
            dependencies: [
                'pendingFoldState',
                'serverFoldState',
            ],
        }),
        followersPartner: many2many('mail.partner', {
            related: 'followers.partner',
        }),
        followers: one2many('mail.follower', {
            inverse: 'followedThread',
        }),
        group_based_subscription: attr({
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
        isCurrentPartnerFollowing: attr({
            compute: '_computeIsCurrentPartnerFollowing',
            default: false,
            dependencies: [
                'followersPartner',
                'messagingCurrentPartner',
            ],
        }),
        isModeratedByCurrentPartner: attr({
            compute: '_computeIsModeratedByCurrentPartner',
            dependencies: [
                'model',
                'messagingCurrentPartner',
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
                'partnerSeenInfos',
                'orderedMessages',
                'messagingCurrentPartner',
            ],
        }),
        lastMessage: many2one('mail.message', {
            compute: '_computeLastMessage',
            dependencies: ['orderedMessages'],
        }),
        lastNeedactionMessage: many2one('mail.message', {
            compute: '_computeLastNeedactionMessage',
            dependencies: ['needactionMessages'],
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
        message_needaction_counter: attr({
            default: 0,
        }),
        message_unread_counter: attr({
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
        moduleIcon: attr(),
        name: attr(),
        needactionMessages: many2many('mail.message', {
            compute: '_computeNeedactionMessages',
            dependencies: ['messages'],
        }),
        orderedMessages: many2many('mail.message', {
            compute: '_computeOrderedMessages',
            dependencies: ['messages'],
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
        partnerSeenInfos: one2many('mail.thread_partner_seen_info', {
            inverse: 'thread',
            isCausal: true,
        }),
        /**
         * Determine if there is a pending fold state change, which is a change
         * of fold state requested by the client but not yet confirmed by the
         * server.
         *
         * This field can be updated to immediately change the fold state on the
         * interface and to notify the server of the new state.
         */
        pendingFoldState: attr(),
        public: attr(),
        seen_message_id: attr(),
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
        uuid: attr(),
        viewers: one2many('mail.thread_viewer', {
            inverse: 'thread',
        }),
        viewersChatWindow: many2many('mail.chat_window', {
            related: 'viewers.chatWindow',
        }),
    };

    Thread.modelName = 'mail.thread';

    return Thread;
}

registerNewModel('mail.thread', factory);

});
