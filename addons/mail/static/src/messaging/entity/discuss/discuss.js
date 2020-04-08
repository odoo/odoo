odoo.define('mail.messaging.entity.Discuss', function (require) {
'use strict';

const { registerNewEntity } = require('mail.messaging.entity.core');

function DiscussFactory({ Entity }) {

    class Discuss extends Entity {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @param {mail.messaging.entity.Thread} thread
         * @returns {string}
         */
        static threadToActiveId(thread) {
            return `${thread.model}_${thread.id}`;
        }

        /**
         * @returns {string|undefined}
         */
        get activeId() {
            if (!this.thread) {
                return undefined;
            }
            return this.constructor.threadToActiveId(this.thread);
        }

        /**
         * @param {mail.messaging.entity.Thread} thread
         */
        cancelRenaming(thread) {
            this.unlink({ renamingThreads: thread });
        }

        clearIsAddingItem() {
            this.update({
                addingChannelValue: "",
                isAddingChannel: false,
                isAddingChat: false,
            });
        }

        clearReplyingToMessage() {
            this.unlink({ replyingToMessage: null });
        }

        /**
         * Close the discuss app. Should reset its internal state.
         */
        close() {
            this.update({ isOpen: false });
        }

        /**
         * @param {Event} ev
         * @param {Object} ui
         * @param {Object} ui.item
         * @param {integer} ui.item.id
         */
        handleAddChannelAutocompleteSelect(ev, ui) {
            if (ui.item.special) {
                this.env.entities.Thread.createChannel({
                    autoselect: true,
                    name: this.addingChannelValue,
                    public: ui.item.special,
                    type: 'channel',
                });
            } else {
                this.env.entities.Thread.joinChannel(ui.item.id, { autoselect: true });
            }
            this.clearIsAddingItem();
        }

        /**
         * @param {Object} req
         * @param {string} req.term
         * @param {function} res
         */
        async handleAddChannelAutocompleteSource(req, res) {
            const value = _.escape(req.term);
            this.update({ addingChannelValue: value });
            const result = await this.env.rpc({
                model: 'mail.channel',
                method: 'channel_search_to_join',
                args: [value],
            });
            const items = result.map(data => {
                let escapedName = _.escape(data.name);
                return Object.assign(data, {
                    label: escapedName,
                    value: escapedName
                });
            });
            // AKU FIXME
            items.push({
                label: this.env.qweb.renderToString(
                    'mail.messaging.component.Discuss.AutocompleteChannelPublicItem',
                    { searchVal: value }
                ),
                value,
                special: 'public'
            }, {
                label: this.env.qweb.renderToString(
                    'mail.messaging.component.Discuss.AutocompleteChannelPrivateItem',
                    { searchVal: value }
                ),
                value,
                special: 'private'
            });
            res(items);
        }

        /**
         * @param {Event} ev
         * @param {Object} ui
         * @param {Object} ui.item
         * @param {integer} ui.item.id
         */
        handleAddChatAutocompleteSelect(ev, ui) {
            const partnerId = ui.item.id;
            const partner = this.env.entities.Partner.fromId(partnerId);
            const chat = partner.directPartnerThread;
            if (chat) {
                this._openThread(chat.localId);
            } else {
                this.env.entities.Thread.createChannel({
                    autoselect: true,
                    partnerId,
                    type: 'chat',
                });
            }
            this.clearIsAddingItem();
        }

        /**
         * @param {Object} req
         * @param {string} req.term
         * @param {function} res
         */
        handleAddChatAutocompleteSource(req, res) {
            const value = _.escape(req.term);
            this.env.entities.Partner.imSearch({
                callback: partners => {
                    const suggestions = partners.map(partner => {
                        return {
                            id: partner.id,
                            value: partner.nameOrDisplayName,
                            label: partner.nameOrDisplayName,
                        };
                    });
                    res(_.sortBy(suggestions, 'label'));
                },
                keyword: value,
                limit: 10,
            });
        }

        /**
         * @returns {boolean}
         */
        get isReplyingToMessage() {
            return !!this.replyingToMessage;
        }

        /**
         * @param {Object} param0
         * @param {function} param0.dispatch
         * @param {Object} param0.getters
         */
        openInitThread() {
            const [model, id] = this.initActiveId.split('_');
            const thread = this.env.entities.Thread.fromModelAndId({
                id: model !== 'mail.box' ? Number(id) : id,
                model,
            });
            if (!thread) {
                return;
            }
            this.update({ thread, threadStringifiedDomain: '[]' });
            thread.open({ resetDiscussDomain: true });
        }

        /**
         * @param {mail.messaging.entity.Thread} thread
         */
        setRenaming(thread) {
            this.link({ renamingThreads: thread });
        }

        /**
         * @returns {mail.messaging.entity.Thread|undefined}
         */
        get thread() {
            return this.threadViewer && this.threadViewer.thread;
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        _update(data) {
            if (!this.threadViewer) {
                const threadViewer = this.env.entities.ThreadViewer.create();
                this.link({ threadViewer });
            }
            if (!this.isOpen) {
                this.isOpen = false;
            }
            if (!this.activeMobileNavbarTabId) {
                this.activeMobileNavbarTabId = 'mailbox';
            }

            const wasOpen = this.isOpen;
            const prevActiveMobileNavbarTabId = this.activeMobileNavbarTabId;

            const {
                /**
                 * Active mobile navbar tab, either 'mailbox', 'chat', or 'channel'.
                 */
                activeMobileNavbarTabId = this.activeMobileNavbarTabId,
                /**
                 * Value that is used to create a channel from the sidebar.
                 */
                addingChannelValue = this.addingChannelValue || "",
                /**
                 * Determine if the moderation discard dialog is displayed.
                 */
                hasModerationDiscardDialog = this.hasModerationDiscardDialog || false,
                /**
                 * Determine if the moderation reject dialog is displayed.
                 */
                hasModerationRejectDialog = this.hasModerationRejectDialog || false,
                /**
                 * Formatted init thread on opening discuss for the first time,
                 * when no active thread is defined. Useful to set a thread to
                 * open without knowing its local id in advance.
                 * format: <threadModel>_<threadId>
                 */
                initActiveId = this.initActiveId,
                /**
                 * Determine whether current user is currently adding a channel from
                 * the sidebar.
                 */
                isAddingChannel = this.isAddingChannel || false,
                /**
                 * Determine whether current user is currently adding a chat from
                 * the sidebar.
                 */
                isAddingChat = this.isAddingChat || false,
                /**
                 * Whether the discuss app is open or not. Useful to determine
                 * whether the discuss or chat window logic should be applied.
                 */
                isOpen = this.isOpen,
                /**
                 * The menu_id of discuss app, received on mail/init_messaging and
                 * used to open discuss from elsewhere.
                 */
                menu_id = this.menu_id || null,
                /**
                 * Quick search input value in the discuss sidebar (desktop). Useful
                 * to filter channels and chats based on this input content.
                 */
                sidebarQuickSearchValue = this.sidebarQuickSearchValue || "",
                thread: threadOrLocalId,
                /**
                 * Domain of the messages in the thread. Determine the thread cache
                 * to use with provided thread local Id.
                 */
                threadStringifiedDomain,
            } = data;

            Object.assign(this, {
                activeMobileNavbarTabId: activeMobileNavbarTabId
                    ? activeMobileNavbarTabId
                    : this.activeMobileNavbarTabId,
                addingChannelValue,
                defaultInitActiveId: 'mail.box_inbox',
                hasModerationDiscardDialog,
                hasModerationRejectDialog,
                initActiveId,
                isAddingChannel,
                isAddingChat,
                isOpen,
                menu_id,
                sidebarQuickSearchValue,
            });

            if (threadStringifiedDomain) {
                this.threadViewer.update({ stringifiedDomain: threadStringifiedDomain });
            }

            const inboxMailbox = this.env.entities.Thread.mailboxFromId('inbox');
            if (threadOrLocalId) {
                const thread = this.env.entities.Thread.get(threadOrLocalId);
                this.threadViewer.update({ thread });
                this.initActiveId = this.constructor.threadToActiveId(thread.model);
            } else if (
                prevActiveMobileNavbarTabId !== this.activeMobileNavbarTabId &&
                this.activeMobileNavbarTabId === 'mailbox' &&
                inboxMailbox
            ) {
                this.threadViewer.update({ thread: inboxMailbox });
            }

            if (wasOpen !== this.isOpen) {
                if (!this.isOpen) {
                    Object.assign(this, {
                        addingChannelValue: "",
                        initActiveId: this.defaultInitActiveId,
                        isAddingChannel: false,
                        isAddingChat: false,
                    });
                    this.unlink({ replyingToMessage: null });
                }
            }
        }

    }

    Object.assign(Discuss, {
        relations: Object.assign({}, Entity.relations, {
            messaging: {
                inverse: 'discuss',
                to: 'Messaging',
                type: 'one2one',
            },
            renamingThreads: {
                inverse: 'renamingDiscuss',
                to: 'Thread',
                type: 'one2many',
            },
            replyingToMessage: {
                inverse: 'replyingToDiscuss',
                to: 'Message',
                type: 'one2one',
            },
            threadViewer: {
                inverse: 'discuss',
                isCausal: true,
                to: 'ThreadViewer',
                type: 'one2one',
            },
        }),
    });

    return Discuss;
}

registerNewEntity('Discuss', DiscussFactory);

});
