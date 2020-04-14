odoo.define('mail.messaging.entity.Thread', function (require) {
'use strict';

const {
    fields: {
        many2many,
        many2one,
        one2many,
        one2one,
    },
    registerNewEntity,
} = require('mail.messaging.entity.core');

function ThreadFactory({ Entity }) {

    class Thread extends Entity {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @static
         * @returns {mail.messaging.entity.Thread[]}
         */
        static get allChannels() {
            return this.all.filter(thread => thread.model === 'mail.channel');
        }

        /**
         * @static
         * @returns {mail.messaging.entity.Thread[]}
         */
        static get allMailboxes() {
            return this.all.filter(thread => thread.model === 'mail.box');
        }

        /**
         * @static
         * @returns {mail.messaging.entity.Thread[]}
         */
        static get allOrderedAndPinnedChannels() {
            return this.allChannels.sort((c1, c2) => c1.displayName < c2.displayName ? -1 : 1);
        }

        /**
         * @static
         * @returns {mail.messaging.entity.Thread[]}
         */
        static get allOrderedAndPinnedChats() {
            return this.allPinnedChannels
                .filter(channel => channel.channel_type === 'chat')
                .sort((c1, c2) => c1.displayName < c2.displayName ? -1 : 1);
        }

        /**
         * @static
         * @returns {mail.messaging.entity.Thread[]}
         */
        static get allOrderedAndPinnedMultiUserChannels() {
            return this.allPinnedChannels
                .filter(channel => channel.channel_type === 'channel')
                .sort((c1, c2) => c1.displayName < c2.displayName ? -1 : 1);
        }

        /**
         * @static
         * @returns {mail.messaging.entity.Thread[]}
         */
        static get allOrderedAndPinnedMailboxes() {
            return this.allMailboxes
                .filter(mailbox => mailbox.isPinned)
                .sort((mailbox1, mailbox2) => {
                    if (mailbox1.id === 'inbox') {
                        return -1;
                    }
                    if (mailbox2.id === 'inbox') {
                        return 1;
                    }
                    if (mailbox1.id === 'starred') {
                        return -1;
                    }
                    if (mailbox2.id === 'starred') {
                        return 1;
                    }
                    const mailbox1Name = mailbox1.displayName;
                    const mailbox2Name = mailbox2.displayName;
                    mailbox1Name < mailbox2Name ? -1 : 1;
                });
        }

        /**
         * @static
         * @returns {mail.messaging.entity.Thread[]}
         */
        static get allPinnedChannels() {
            return this.allChannels.filter(channel => channel.isPinned);
        }

        /**
         * @static
         * @returns {mail.messaging.entity.Thread[]}
         */
        static get allUnreadChannels() {
            return this.allChannels.filter(
                channel => channel.message_unread_counter > 0
            );
        }

        /**
         * @static
         * @param {integer} id
         * @returns {mail.messaging.entity.Thread|undefined}
         */
        static channelFromId(id) {
            return this.allChannels.find(channel => channel.id === id);
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
            const data = await this.env.rpc({
                model: 'mail.channel',
                method: type === 'chat' ? 'channel_get' : 'channel_create',
                args: type === 'chat' ? [[partnerId]] : [name, publicStatus],
                kwargs: {
                    context: Object.assign({}, this.env.session.user_content, {
                        isMobile: device.isMobile,
                    }),
                }
            });
            const thread = this.create(Object.assign({}, data, { isPinned: true }));
            if (autoselect) {
                thread.open({ chatWindowMode: autoselectChatWindowMode });
            }
        }

        /**
         * @static
         * @param {Object} param0
         * @param {integer} param0.id
         * @param {string} param0.model
         * @returns {mail.messaging.entity.Thread|undefined}
         */
        static fromModelAndId({ id, model }) {
            const allThreads = this.all;
            return allThreads.find(thread => thread.model === model && thread.id === id);
        }

        /**
         * Join a channel. This channel may not yet exists in the store.
         *
         * @static
         * @param {integer} channelId
         * @param {Object} param1
         * @param {boolean} [param1.autoselect=false]
         */
        static async joinChannel(channelId, { autoselect = false } = {}) {
            const channel = this.channelFromId(channelId);
            if (channel) {
                return;
            }
            const data = await this.env.rpc({
                model: 'mail.channel',
                method: 'channel_join_and_get_info',
                args: [[channelId]]
            });
            const thread = this.create(Object.assign({}, data, { isPinned: true }));
            if (autoselect) {
                thread.open({ resetDiscussDomain: true });
            }
        }

        /**
         * Load the previews of the specified threads. Basically, it fetches the
         * last messages, since they are used to display inline content of them.
         *
         * @static
         * @param {mail.messaging.entity.Thread>[]} threads
         */
        static async loadPreviews(threads) {
            const channelIds = threads.reduce((list, thread) => {
                if (thread.model === 'mail.channel') {
                    return list.concat(thread.id);
                }
                return list;
            }, []);
            const messagePreviews = await this.env.rpc({
                model: 'mail.channel',
                method: 'channel_fetch_preview',
                args: [channelIds],
            }, { shadow: true });
            for (const preview of messagePreviews) {
                const messageData = preview.last_message;
                this.env.entities.Message.insert(messageData);
            }
        }

        /**
         * @static
         * @param {string} id
         * @returns {mail.messaging.entity.Thread|undefined}
         */
        static mailboxFromId(id) {
            return this.allMailboxes.find(mailbox => mailbox.id === id);
        }

        /**
         * @static
         */
        static openNewMessage() {
            const discuss = this.env.messaging.discuss;
            if (discuss.isOpen) {
                discuss.openNewMessage();
            } else {
                this.env.messaging.chatWindowManager.openNewMessage();
            }
        }

        /**
         * @returns {mail.messaging.entity.Attachment[]}
         */
        get allAttachments() {
            return [...this.originThreadAttachments.concat(this.attachments)]
                .sort((a1, a2) => a1.id < a2.id ? 1 : -1);
        }

        /**
         * @param {string} [stringifiedDomain='[]']
         * @returns {mail.messaging.entity.ThreadCache}
         */
        cache(stringifiedDomain = '[]') {
            let cache = this.caches.find(cache => cache.stringifiedDomain === stringifiedDomain);
            if (!cache) {
                cache = this.env.entities.ThreadCache.create({
                    stringifiedDomain,
                    thread: this,
                });
            }
            return cache;
        }

        /**
         * @returns {mail.messaging.entity.ChatWindow[]}
         */
        get chatWindows() {
            const chatWindowViewers = this.viewers.filter(viewer => !!viewer.chatWindow);
            return chatWindowViewers.map(viewer => viewer.chatWindow);
        }

        /**
         * @returns {string}
         */
        get displayName() {
            if (this.channel_type === 'chat' && this.directPartner) {
                return this.custom_channel_name || this.directPartner.nameOrDisplayName;
            }
            if (this.channel_type === 'livechat') {
                // FIXME: should be patch in im_livechat
                return this.correspondent_name;
            }
            return this.name;
        }

        /**
         * Fetch attachments linked to a record. Useful for populating the store
         * with these attachments, which are used by attachment box in the chatter.
         */
        async fetchAttachments() {
            const attachmentsData = await this.env.rpc({
                model: 'ir.attachment',
                method: 'search_read',
                domain: [
                    ['res_id', '=', this.id],
                    ['res_model', '=', this.model],
                ],
                fields: ['id', 'name', 'mimetype'],
                orderBy: [{ name: 'id', asc: false }],
            });
            for (const attachmentData of attachmentsData) {
                this.env.entities.Attachment.insert(Object.assign({
                    res_id: this.id,
                    res_model: this.model,
                }, attachmentData));
            }
            this.update({ areAttachmentsLoaded: true });
        }

        /**
         * @returns {boolean}
         */
        get isModeratedByUser() {
            if (this.model !== 'mail.channel') {
                return false;
            }
            return Thread.moderatedChannelIds.includes(this.id);
        }

        /**
         * @returns {mail.messaging.entity.Message|undefined}
         */
        get lastMessage() {
            return this.mainCache.lastMessage;
        }

        /**
         * Load new messages on the main cache of this thread.
         */
        loadNewMessages() {
            this.mainCache.loadNewMessages();
        }

        /**
         * @returns {mail.messaging.entity.ThreadCache}
         */
        get mainCache() {
            return this.caches.find(cache => cache.stringifiedDomain === '[]');
        }

        /**
         * Mark the specified conversation as read/seen.
         */
        async markAsSeen() {
            if (this.message_unread_counter === 0) {
                return;
            }
            if (this.model === 'mail.channel') {
                const seen_message_id = await this.env.rpc({
                    model: 'mail.channel',
                    method: 'channel_seen',
                    args: [[this.id]]
                }, { shadow: true });
                this.update({ seen_message_id });
            }
            this.update({ message_unread_counter: 0 });
        }

        /**
         * Notify server the fold state of this thread. Useful for cross-tab
         * and cross-device chat window state synchronization.
         */
        async notifyFoldStateToServer() {
            await this.env.rpc({
                model: 'mail.channel',
                method: 'channel_fold',
                kwargs: {
                    uuid: this.uuid,
                    state: this.foldState,
                }
            }, { shadow: true });
        }

        /**
         * Open provided thread, either in discuss app or as a chat window.
         *
         * @param {Object} param0
         * @param {string} [param0.chatWindowMode]
         * @param {boolean} [param0.resetDiscussDomain=false]
         */
        open({ chatWindowMode, resetDiscussDomain = false } = {}) {
            const device = this.env.messaging.device;
            const discuss = this.env.messaging.discuss;
            const messagingMenu = this.env.messaging.messagingMenu;
            if (
                (!device.isMobile && discuss.isOpen) ||
                (device.isMobile && this.model === 'mail.box')
            ) {
                if (resetDiscussDomain) {
                    discuss.update({ threadStringifiedDomain: '[]' });
                }
                discuss.update({ thread: this });
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
                this.env.do_action('mail.action_new_discuss', {
                    clear_breadcrumbs: false,
                    active_id: discuss.threadToActiveId(this),
                    on_reverse_breadcrumb: () => discuss.close(),
                });
            } else {
                this.env.do_action({
                    type: 'ir.actions.act_window',
                    res_model: this.model,
                    views: [[false, 'form']],
                    res_id: this.id,
                });
            }
        }

        /**
         * Rename the given thread with provided new name.
         *
         * @param {string} newName
         */
        async rename(newName) {
            if (this.channel_type === 'chat') {
                await this.env.rpc({
                    model: 'mail.channel',
                    method: 'channel_set_custom_name',
                    args: [this.id],
                    kwargs: {
                        name: newName,
                    },
                });
            }
            this.unlink({ renamingDiscuss: null });
            this.update({ custom_channel_name: newName });
        }

        /**
         * @param {string} newFoldState
         */
        updateFoldState(newFoldState) {
            this.update({
                is_minimized: newFoldState === 'closed' ? false : true,
                state: newFoldState,
            });
        }

        /**
         * Unsubscribe current user from provided channel.
         */
        async unsubscribe() {
            if (this.channel_type === 'mail.channel') {
                return this.env.rpc({
                    model: 'mail.channel',
                    method: 'action_unfollow',
                    args: [[this.id]]
                });
            }
            return this.env.rpc({
                model: 'mail.channel',
                method: 'channel_pin',
                args: [this.uuid, false]
            });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        _createInstanceLocalId(data) {
            const { channel_type, id, isTemporary = false, model } = data;
            let threadModel = model;
            if (!threadModel && channel_type) {
                threadModel = 'mail.channel';
            }
            if (isTemporary) {
                return `${this.constructor.name}_${id}`;
            }
            return `${this.constructor.name}_${threadModel}_${id}`;
        }

        /**
         * @override
         */
        _update(data) {
            const prevFoldState = this.foldState;

            const {
                areAttachmentsLoaded = this.areAttachmentsLoaded || false,
                channel_type = this.channel_type,
                // FIXME: should be patch in im_livechat
                correspondent_name = this.correspondent_name,
                counter = this.counter || 0,
                create_uid = this.create_uid,
                custom_channel_name = this.custom_channel_name,
                direct_partner, direct_partner: [directPartnerData] = [],
                group_based_subscription = this.group_based_subscription || false,
                id = this.id,
                isPinned = this.isPinned || false,
                isTemporary = this.isTemporary || false,
                is_minimized,
                is_moderator = this.is_moderator || false,
                mass_mailing = this.mass_mailing || false,
                members: membersData,
                message_needaction_counter = this.message_needaction_counter || 0,
                message_unread_counter = this.message_unread_counter || 0,
                model = this.model,
                moderation = this.moderation || false,
                name = this.name,
                public: public2 = this.public,
                seen_message_id = this.seen_message_id,
                seen_partners_info = this.seen_partners_info,
                state,
                uuid = this.uuid,
            } = data;

            let threadModel = model;
            if (!threadModel && channel_type) {
                threadModel = 'mail.channel';
            }
            if (!threadModel || !id) {
                throw new Error('thread must always have `model` and `id`');
            }
            let threadIsPinned = isPinned;
            if (threadModel === 'mail.box') {
                threadIsPinned = true;
            }

            let foldState;
            if (is_minimized !== undefined) {
                if (!is_minimized) {
                    foldState = 'closed';
                } else {
                    foldState = state ? state : (this.foldState || 'open');
                }
            } else {
                foldState = this.foldState || 'closed';
            }

            Object.assign(this, {
                areAttachmentsLoaded,
                channel_type,
                correspondent_name,
                counter,
                create_uid,
                custom_channel_name,
                foldState,
                group_based_subscription,
                id,
                isPinned: threadIsPinned,
                isTemporary,
                is_moderator,
                mass_mailing,
                message_needaction_counter,
                message_unread_counter,
                model: threadModel,
                moderation,
                name,
                public: public2,
                seen_message_id,
                seen_partners_info,
                uuid,
            });

            if (this.model === 'mail.channel' && prevFoldState && this.foldState !== prevFoldState) {
                this.notifyFoldStateToServer();
            }

            // chat window
            if (this.foldState !== 'closed' && this.chatWindows.length === 0) {
                this.env.messaging.chatWindowManager.openThread(this);
            }
            if (this.foldState === 'closed' && this.chatWindows.length > 0) {
                for (const chatWindow of this.chatWindows) {
                    chatWindow.close();
                }
            }
            // composer
            if (!this.composer) {
                const composer = this.env.entities.Composer.create();
                this.link({ composer });
            }
            // directPartner
            if (direct_partner) {
                let directPartner = this.env.entities.Partner.insert(directPartnerData);
                this.link({ directPartner });
            }
            // main thread cache
            if (!this.mainCache) {
                this.env.entities.ThreadCache.create({ thread: this });
            }
            // members
            if (membersData) {
                const prevMembers = this.members;
                const newMembers = [];
                for (const memberData of membersData) {
                    let member = this.env.entities.Partner.insert(memberData);
                    newMembers.push(member);
                    this.link({ members: member });
                }
                const oldPrevMembers = prevMembers.filter(member => !newMembers.include(member));
                for (const member of oldPrevMembers) {
                    this.unlink({ members: member });
                }
            }
        }

    }

    Object.assign(Thread, {
        fields: Object.assign({}, Entity.fields, {
            attachments: many2many('Attachment', {
                inverse: 'threads',
            }),
            caches: one2many('ThreadCache', {
                inverse: 'thread',
                isCausal: true,
            }),
            composer: one2one('Composer', {
                inverse: 'thread',
                isCausal: true,
            }),
            directPartner: one2one('Partner', {
                inverse: 'directPartnerThread',
            }),
            members: many2many('Partner', {
                inverse: 'memberThreads',
            }),
            originThreadAttachments: one2many('Attachment', {
                inverse: 'originThread',
            }),
            originThreadMessages: one2many('Message', {
                inverse: 'originThread',
            }),
            renamingDiscuss: many2one('Discuss', {
                inverse: 'renamingThreads',
            }),
            typingMembers: many2many('Partner', {
                inverse: 'typingMemberThreads',
            }),
            viewers: one2many('ThreadViewer', {
                inverse: 'thread',
            }),
        }),
        moderatedChannelIds: [],
    });

    return Thread;
}

registerNewEntity('Thread', ThreadFactory);

});
