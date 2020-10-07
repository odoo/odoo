odoo.define('mail/static/src/models/discuss.discuss.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2one, one2many, one2one } = require('mail/static/src/model/model_field.js');
const { clear } = require('mail/static/src/model/model_field_command.js');

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

        focus() {
            this.update({ isDoFocus: true });
        }

        /**
         * @param {Event} ev
         * @param {Object} ui
         * @param {Object} ui.item
         * @param {integer} ui.item.id
         */
        async handleAddChannelAutocompleteSelect(ev, ui) {
            const name = this.addingChannelValue;
            this.clearIsAddingItem();
            if (ui.item.special) {
                const channel = await this.async(() =>
                    this.env.models['mail.thread'].performRpcCreateChannel({
                        name,
                        privacy: ui.item.special,
                    })
                );
                channel.open();
            } else {
                const channel = await this.async(() =>
                    this.env.models['mail.thread'].performRpcJoinChannel({
                        channelId: ui.item.id,
                    })
                );
                channel.open();
            }
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
            const domain = [
                ['channel_type', '=', 'channel'],
                ['name', 'ilike', value],
            ];
            const fields = ['channel_type', 'name', 'public', 'uuid'];
            const result = await this.async(() => this.env.services.rpc({
                model: "mail.channel",
                method: "search_read",
                kwargs: {
                    domain,
                    fields,
                },
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
            this.env.messaging.openChat({ partnerId: ui.item.id });
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
            const [model, id] = typeof this.initActiveId === 'number'
                ? ['mail.channel', this.initActiveId]
                : this.initActiveId.split('_');
            const thread = this.env.models['mail.thread'].findFromIdentifyingData({
                id: model !== 'mail.box' ? Number(id) : id,
                model,
            });
            if (!thread) {
                return;
            }
            thread.open();
            if (this.env.messaging.device.isMobile && thread.channel_type) {
                this.update({ activeMobileNavbarTabId: thread.channel_type });
            }
        }


        /**
         * Opens the given thread in Discuss, and opens Discuss if necessary.
         *
         * @param {mail.thread} thread
         */
        async openThread(thread) {
            this.update({
                thread: [['link', thread]],
            });
            this.focus();
            if (!this.isOpen) {
                this.env.bus.trigger('do-action', {
                    action: 'mail.action_discuss',
                    options: {
                        active_id: this.threadToActiveId(this),
                        clear_breadcrumbs: false,
                        on_reverse_breadcrumb: () => this.close(),
                    },
                });
            }
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
            // avoid to reply to a note by a message and vice-versa.
            // subject to change later by allowing subtype choice.
            this.replyingToMessageOriginThreadComposer.update({
                isLog: !message.is_discussion && !message.is_notification
            });
            this.focus();
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
                return clear();
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
         * @returns {boolean}
         */
        _computeHasThreadView() {
            if (!this.thread || !this.isOpen) {
                return false;
            }
            if (
                this.env.messaging.device.isMobile &&
                (
                    this.activeMobileNavbarTabId !== 'mailbox' ||
                    this.thread.model !== 'mail.box'
                )
            ) {
                return false;
            }
            return true;
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
         * Only pinned threads are allowed in discuss.
         *
         * @private
         * @returns {mail.thread|undefined}
         */
        _computeThread() {
            let thread = this.thread;
            if (this.env.messaging &&
                this.env.messaging.inbox &&
                this.env.messaging.device.isMobile &&
                this.activeMobileNavbarTabId === 'mailbox' &&
                this.initActiveId !== 'mail.box_inbox' &&
                !thread
            ) {
                // After loading Discuss from an arbitrary tab other then 'mailbox',
                // switching to 'mailbox' requires to also set its inner-tab ;
                // by default the 'inbox'.
                return [['replace', this.env.messaging.inbox]];
            }
            if (!thread || !thread.isPinned) {
                return [['unlink']];
            }
            return [];
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
        /**
         * Serves as compute dependency.
         */
        device: one2one('mail.device', {
            related: 'messaging.device',
        }),
        /**
         * Serves as compute dependency.
         */
        deviceIsMobile: attr({
            related: 'device.isMobile',
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
         * Determines whether `this.thread` should be displayed.
         */
        hasThreadView: attr({
            compute: '_computeHasThreadView',
            dependencies: [
                'activeMobileNavbarTabId',
                'deviceIsMobile',
                'isOpen',
                'thread',
                'threadModel',
            ],
        }),
        /**
         * Formatted init thread on opening discuss for the first time,
         * when no active thread is defined. Useful to set a thread to
         * open without knowing its local id in advance.
         * Support two formats:
         *    {string} <threadModel>_<threadId>
         *    {int} <channelId> with default model of 'mail.channel'
         */
        initActiveId: attr({
            default: 'mail.box_inbox',
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
         * Determine whether this discuss should be focused at next render.
         */
        isDoFocus: attr({
            default: false,
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
        messagingInbox: many2one('mail.thread', {
            related: 'messaging.inbox',
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
        /**
         * Determines the domain to apply when fetching messages for `this.thread`.
         * This value should only be written by the control panel.
         */
        stringifiedDomain: attr({
            default: '[]',
        }),
        /**
         * Determines the `mail.thread` that should be displayed by `this`.
         */
        thread: many2one('mail.thread', {
            compute: '_computeThread',
            dependencies: [
                'activeMobileNavbarTabId',
                'deviceIsMobile',
                'isThreadPinned',
                'messaging',
                'messagingInbox',
                'thread',
                'threadModel',
            ],
        }),
        threadId: attr({
            related: 'thread.id',
        }),
        threadModel: attr({
            related: 'thread.model',
        }),
        /**
         * States the `mail.thread_view` displaying `this.thread`.
         */
        threadView: one2one('mail.thread_view', {
            related: 'threadViewer.threadView',
        }),
        /**
         * Determines the `mail.thread_viewer` managing the display of `this.thread`.
         */
        threadViewer: one2one('mail.thread_viewer', {
            default: [['create']],
            inverse: 'discuss',
            isCausal: true,
        }),
    };

    Discuss.modelName = 'mail.discuss';

    return Discuss;
}

registerNewModel('mail.discuss', factory);

});
