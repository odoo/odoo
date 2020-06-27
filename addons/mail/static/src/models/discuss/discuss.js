odoo.define('mail/static/src/models/discuss.discuss.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2one, one2many, one2one } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    class Discuss extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @param {mail.thread} thread
         */
        cancelThreadRenaming(thread) {
            this.update({ renamingThreads: [['unlink', thread]] });
        }

        clearIsAddingItem() {
            this.update({
                addingChannelValue: "",
                isAddingChannel: false,
                isAddingChat: false,
            });
        }

        clearReplyingToMessage() {
            this.update({ replyingToMessage: [['unlink-all']] });
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
                this.env.models['mail.thread'].createChannel({
                    autoselect: true,
                    name: this.addingChannelValue,
                    public: ui.item.special,
                    type: 'channel',
                });
            } else {
                this.env.models['mail.thread'].joinChannel(ui.item.id, { autoselect: true });
            }
            this.clearIsAddingItem();
        }

        /**
         * @param {Object} req
         * @param {string} req.term
         * @param {function} res
         */
        async handleAddChannelAutocompleteSource(req, res) {
            const value = req.term;
            const escapedValue = owl.utils.escape(value);
            this.update({ addingChannelValue: value });
            const result = await this.async(() => this.env.services.rpc({
                model: 'mail.channel',
                method: 'channel_search_to_join',
                args: [value],
            }));
            const items = result.map(data => {
                let escapedName = owl.utils.escape(data.name);
                return Object.assign(data, {
                    label: escapedName,
                    value: escapedName
                });
            });
            // XDU FIXME could use a component but be careful with owl's
            // renderToString https://github.com/odoo/owl/issues/708
            items.push({
                label: _.str.sprintf(
                    `<strong>${this.env._t('Create %s')}</strong>`,
                    `<em><span class="fa fa-hashtag"/>${escapedValue}</em>`,
                ),
                escapedValue,
                special: 'public'
            }, {
                label: _.str.sprintf(
                    `<strong>${this.env._t('Create %s')}</strong>`,
                    `<em><span class="fa fa-lock"/>${escapedValue}</em>`,
                ),
                escapedValue,
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
            const partner = this.env.models['mail.partner'].find(partner =>
                partner.id === partnerId
            );
            const chat = partner.correspondentThreads.find(thread => thread.channel_type === 'chat');
            if (chat) {
                this.threadViewer.update({ thread: [['link', chat]] });
            } else {
                this.env.models['mail.thread'].createChannel({
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
            const value = owl.utils.escape(req.term);
            this.env.models['mail.partner'].imSearch({
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
         * Open thread from init active id. `initActiveId` is used to refer to
         * a thread that we may not have full data yet, such as when messaging
         * is not yet initialized.
         */
        openInitThread() {
            const [model, id] = this.initActiveId.split('_');
            const thread = this.env.models['mail.thread'].find(thread =>
                thread.id === (model !== 'mail.box' ? Number(id) : id) &&
                thread.model === model
            );
            if (!thread) {
                return;
            }
            this.threadViewer.update({
                stringifiedDomain: '[]',
                thread: [['link', thread]],
            });
            thread.open({ resetDiscussDomain: true });
        }

        /**
         * @param {mail.thread} thread
         * @param {string} newName
         */
        async renameThread(thread, newName) {
            await this.async(() => thread.rename(newName));
            this.update({ renamingThreads: [['unlink', thread]] });
        }

        /**
         * Action to initiate reply to given message in Inbox. Assumes that
         * Discuss and Inbox are already opened.
         *
         * @param {mail.message} message
         */
        replyToMessage(message) {
            this.update({ replyingToMessage: [['link', message]] });
            this.replyingToMessageOriginThreadComposer.focus();
        }

        /**
         * @param {mail.thread} thread
         */
        setThreadRenaming(thread) {
            this.update({ renamingThreads: [['link', thread]] });
        }

        /**
         * @param {mail.thread} thread
         * @returns {string}
         */
        threadToActiveId(thread) {
            return `${thread.model}_${thread.id}`;
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeActiveId() {
            if (!this.thread) {
                return undefined;
            }
            return this.threadToActiveId(this.thread);
        }

        /**
         * @private
         * @returns {string}
         */
        _computeAddingChannelValue() {
            if (!this.isOpen) {
                return "";
            }
            return this.addingChannelValue;
        }

        /**
         * @private
         * @returns {string}
         */
        _computeInitActiveId() {
            if (!this.isOpen) {
                return this.defaultInitActiveId;
            }
            if (this.thread) {
                return this.threadToActiveId(this.thread);
            }
            return this.initActiveId;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsAddingChannel() {
            if (!this.isOpen) {
                return false;
            }
            return this.isAddingChannel;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsAddingChat() {
            if (!this.isOpen) {
                return false;
            }
            return this.isAddingChat;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsReplyingToMessage() {
            return !!this.replyingToMessage;
        }

        /**
         * Ensures the reply feature is disabled if discuss is not open.
         *
         * @private
         * @returns {mail.message|undefined}
         */
        _computeReplyingToMessage() {
            if (!this.isOpen) {
                return [['unlink-all']];
            }
            return [];
        }

        /**
         * @private
         */
        _onChangeThreadIsPinned() {
            let thread = this.thread;
            // No thread, or thread is being removed
            // so we display discuss the messaging's Inbox.
            if (
                (!thread || !thread.isPinned) &&
                this.messaging
            ) {
                thread = this.messaging.inbox;
            }
            if (thread && this.threadViewer && thread !== this.thread) {
                this.threadViewer.update({ thread: [['link', thread]] });
            }
        }
    }

    Discuss.fields = {
        activeId: attr({
            compute: '_computeActiveId',
            dependencies: [
                'thread',
                'threadId',
                'threadModel',
            ],
        }),
        /**
         * Active mobile navbar tab, either 'mailbox', 'chat', or 'channel'.
         */
        activeMobileNavbarTabId: attr({
            default: 'mailbox',
        }),
        /**
         * Value that is used to create a channel from the sidebar.
         */
        addingChannelValue: attr({
            compute: '_computeAddingChannelValue',
            default: "",
            dependencies: ['isOpen'],
        }),
        defaultInitActiveId: attr({
            default: 'mail.box_inbox',
        }),
        /**
         * Determine if the moderation discard dialog is displayed.
         */
        hasModerationDiscardDialog: attr({
            default: false,
        }),
        /**
         * Determine if the moderation reject dialog is displayed.
         */
        hasModerationRejectDialog: attr({
            default: false,
        }),
        /**
         * Formatted init thread on opening discuss for the first time,
         * when no active thread is defined. Useful to set a thread to
         * open without knowing its local id in advance.
         * format: <threadModel>_<threadId>
         */
        initActiveId: attr({
            compute: '_computeInitActiveId',
            default: 'mail.box_inbox',
            dependencies: [
                'isOpen',
                'thread',
                'threadId',
                'threadModel',
            ],
        }),
        /**
         * Determine whether current user is currently adding a channel from
         * the sidebar.
         */
        isAddingChannel: attr({
            compute: '_computeIsAddingChannel',
            default: false,
            dependencies: ['isOpen'],
        }),
        /**
         * Determine whether current user is currently adding a chat from
         * the sidebar.
         */
        isAddingChat: attr({
            compute: '_computeIsAddingChat',
            default: false,
            dependencies: ['isOpen'],
        }),
        /**
         * Whether the discuss app is open or not. Useful to determine
         * whether the discuss or chat window logic should be applied.
         */
        isOpen: attr({
            default: false,
        }),
        isReplyingToMessage: attr({
            compute: '_computeIsReplyingToMessage',
            default: false,
            dependencies: ['replyingToMessage'],
        }),
        isThreadPinned: attr({
            related: 'thread.isPinned',
        }),
        /**
         * The menu_id of discuss app, received on mail/init_messaging and
         * used to open discuss from elsewhere.
         */
        menu_id: attr({
            default: null,
        }),
        messaging: one2one('mail.messaging', {
            inverse: 'discuss',
        }),
        /**
         * When a thread changes, or some properties of it change
         * Computes whether we should display it or change it
         */
        onChangeThreadIsPinned: attr({
            compute: '_onChangeThreadIsPinned',
            dependencies: [
                'isThreadPinned',
                'thread',
            ],
        }),
        renamingThreads: one2many('mail.thread'),
        /**
         * The message that is currently selected as being replied to in Inbox.
         * There is only one reply composer shown at a time, which depends on
         * this selected message.
         */
        replyingToMessage: many2one('mail.message', {
            compute: '_computeReplyingToMessage',
            dependencies: [
                'isOpen',
                'replyingToMessage',
            ],
        }),
        /**
         * The thread concerned by the reply feature in Inbox. It depends on the
         * message set to be replied, and should be considered read-only.
         */
        replyingToMessageOriginThread: many2one('mail.thread', {
            related: 'replyingToMessage.originThread',
        }),
        /**
         * The composer to display for the reply feature in Inbox. It depends
         * on the message set to be replied, and should be considered read-only.
         */
        replyingToMessageOriginThreadComposer: one2one('mail.composer', {
            inverse: 'discussAsReplying',
            related: 'replyingToMessageOriginThread.composer',
        }),
        /**
         * Quick search input value in the discuss sidebar (desktop). Useful
         * to filter channels and chats based on this input content.
         */
        sidebarQuickSearchValue: attr({
            default: "",
        }),
        thread: many2one('mail.thread', {
            related: 'threadViewer.thread',
        }),
        threadId: attr({
            related: 'thread.id',
        }),
        threadModel: attr({
            related: 'thread.model',
        }),
        threadViewer: one2one('mail.thread_viewer', {
            autocreate: true,
            isCausal: true,
        }),
    };

    Discuss.modelName = 'mail.discuss';

    return Discuss;
}

registerNewModel('mail.discuss', factory);

});
