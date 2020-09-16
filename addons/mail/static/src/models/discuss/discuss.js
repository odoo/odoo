odoo.define('mail/static/src/models/discuss.discuss.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { clear } = require('mail/static/src/model/model_field_command.js');
const { attr, many2one, one2many, one2one } = require('mail/static/src/model/model_field_utils.js');

function factory(dependencies) {

    class Discuss extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @param {mail.thread} thread
         */
        cancelThreadRenaming(thread) {
            this.update({ __mfield_renamingThreads: [['unlink', thread]] });
        }

        clearIsAddingItem() {
            this.update({
                __mfield_addingChannelValue: "",
                __mfield_isAddingChannel: false,
                __mfield_isAddingChat: false,
            });
        }

        clearReplyingToMessage() {
            this.update({ __mfield_replyingToMessage: [['unlink-all']] });
        }

        /**
         * Close the discuss app. Should reset its internal state.
         */
        close() {
            this.update({ __mfield_isOpen: false });
        }

        focus() {
            this.update({ __mfield_isDoFocus: true });
        }

        /**
         * @param {Event} ev
         * @param {Object} ui
         * @param {Object} ui.item
         * @param {integer} ui.item.id
         */
        async handleAddChannelAutocompleteSelect(ev, ui) {
            const name = this.__mfield_addingChannelValue;
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
            this.update({ __mfield_addingChannelValue: value });
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
                            id: partner.__mfield_id(this),
                            value: partner.__mfield_nameOrDisplayName(this),
                            label: partner.__mfield_nameOrDisplayName(this),
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
            const [model, id] = typeof this.__mfield_initActiveId(this) === 'number'
                ? ['mail.channel', this.__mfield_initActiveId(this)]
                : this.__mfield_initActiveId(this).split('_');
            const thread = this.env.models['mail.thread'].findFromIdentifyingData({
                __mfield_id: model !== 'mail.box' ? Number(id) : id,
                __mfield_model: model,
            });
            if (!thread) {
                return;
            }
            thread.open();
            if (this.env.messaging.__mfield_device(this).__mfield_isMobile(this) && thread.__mfield_channel_type(this)) {
                this.update({ __mfield_activeMobileNavbarTabId: thread.__mfield_channel_type(this) });
            }
        }


        /**
         * Opens the given thread in Discuss, and opens Discuss if necessary.
         *
         * @param {mail.thread} thread
         */
        async openThread(thread) {
            this.update({
                __mfield_stringifiedDomain: '[]',
                __mfield_thread: [['link', thread]],
            });
            this.focus();
            if (!this.__mfield_isOpen(this)) {
                this.env.bus.trigger('do-action', {
                    action: 'mail.action_discuss',
                    options: {
                        active_id: this.threadToActiveId(this.__mfield_thread(this)),
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
            this.update({
                __mfield_renamingThreads: [['unlink', thread]],
            });
        }

        /**
         * Action to initiate reply to given message in Inbox. Assumes that
         * Discuss and Inbox are already opened.
         *
         * @param {mail.message} message
         */
        replyToMessage(message) {
            this.update({
                __mfield_replyingToMessage: [['link', message]],
            });
            // avoid to reply to a note by a message and vice-versa.
            // subject to change later by allowing subtype choice.
            this.__mfield_replyingToMessageOriginThreadComposer(this).update({
                __mfield_isLog: (
                    !message.__mfield_is_discussion(this) &&
                    !message.__mfield_is_notification(this)
                ),
            });
            this.focus();
        }

        /**
         * @param {mail.thread} thread
         */
        setThreadRenaming(thread) {
            this.update({
                __mfield_renamingThreads: [['link', thread]],
            });
        }

        /**
         * @param {mail.thread} thread
         * @returns {string}
         */
        threadToActiveId(thread) {
            return `${thread.__mfield_model(this)}_${thread.__mfield_id(this)}`;
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeActiveId() {
            if (!this.__mfield_thread(this)) {
                return clear();
            }
            return this.threadToActiveId(this.__mfield_thread(this));
        }

        /**
         * @private
         * @returns {string}
         */
        _computeAddingChannelValue() {
            if (!this.__mfield_isOpen(this)) {
                return "";
            }
            return this.__mfield_addingChannelValue(this);
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasThreadView() {
            if (!this.__mfield_thread(this) || !this.__mfield_isOpen(this)) {
                return false;
            }
            if (
                this.env.messaging.__mfield_device(this).__mfield_isMobile(this) &&
                (
                    this.__mfield_activeMobileNavbarTabId(this) !== 'mailbox' ||
                    this.__mfield_thread(this).__mfield_model(this) !== 'mail.box'
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
            if (!this.__mfield_isOpen(this)) {
                return false;
            }
            return this.__mfield_isAddingChannel(this);
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsAddingChat() {
            if (!this.__mfield_isOpen(this)) {
                return false;
            }
            return this.__mfield_isAddingChat(this);
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsReplyingToMessage() {
            return !!this.__mfield_replyingToMessage(this);
        }

        /**
         * Ensures the reply feature is disabled if discuss is not open.
         *
         * @private
         * @returns {mail.message|undefined}
         */
        _computeReplyingToMessage() {
            if (!this.__mfield_isOpen(this)) {
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
            let thread = this.__mfield_thread(this);
            if (
                this.env.messaging &&
                this.env.messaging.__mfield_inbox(this) &&
                this.env.messaging.__mfield_device(this).__mfield_isMobile(this) &&
                this.__mfield_activeMobileNavbarTabId(this) === 'mailbox' &&
                this.__mfield_initActiveId(this) !== 'mail.box_inbox' &&
                !thread
            ) {
                // After loading Discuss from an arbitrary tab other then 'mailbox',
                // switching to 'mailbox' requires to also set its inner-tab ;
                // by default the 'inbox'.
                return [['replace', this.env.messaging.__mfield_inbox(this)]];
            }
            if (!thread || !thread.__mfield_isPinned(this)) {
                return [['unlink']];
            }
            return [];
        }

    }

    Discuss.fields = {
        __mfield_activeId: attr({
            compute: '_computeActiveId',
            dependencies: [
                '__mfield_thread',
                '__mfield_threadId',
                '__mfield_threadModel',
            ],
        }),
        /**
         * Active mobile navbar tab, either 'mailbox', 'chat', or 'channel'.
         */
        __mfield_activeMobileNavbarTabId: attr({
            default: 'mailbox',
        }),
        /**
         * Value that is used to create a channel from the sidebar.
         */
        __mfield_addingChannelValue: attr({
            compute: '_computeAddingChannelValue',
            default: "",
            dependencies: [
                '__mfield_isOpen',
            ],
        }),
        /**
         * Serves as compute dependency.
         */
        __mfield_device: one2one('mail.device', {
            related: '__mfield_messaging.__mfield_device',
        }),
        /**
         * Serves as compute dependency.
         */
        __mfield_deviceIsMobile: attr({
            related: '__mfield_device.__mfield_isMobile',
        }),
        /**
         * Determine if the moderation discard dialog is displayed.
         */
        __mfield_hasModerationDiscardDialog: attr({
            default: false,
        }),
        /**
         * Determine if the moderation reject dialog is displayed.
         */
        __mfield_hasModerationRejectDialog: attr({
            default: false,
        }),
        /**
         * Determines whether `this.thread` should be displayed.
         */
        __mfield_hasThreadView: attr({
            compute: '_computeHasThreadView',
            dependencies: [
                '__mfield_activeMobileNavbarTabId',
                '__mfield_deviceIsMobile',
                '__mfield_isOpen',
                '__mfield_thread',
                '__mfield_threadModel',
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
        __mfield_initActiveId: attr({
            default: 'mail.box_inbox',
        }),
        /**
         * Determine whether current user is currently adding a channel from
         * the sidebar.
         */
        __mfield_isAddingChannel: attr({
            compute: '_computeIsAddingChannel',
            default: false,
            dependencies: [
                '__mfield_isOpen',
            ],
        }),
        /**
         * Determine whether current user is currently adding a chat from
         * the sidebar.
         */
        __mfield_isAddingChat: attr({
            compute: '_computeIsAddingChat',
            default: false,
            dependencies: [
                '__mfield_isOpen',
            ],
        }),
        /**
         * Determine whether this discuss should be focused at next render.
         */
        __mfield_isDoFocus: attr({
            default: false,
        }),
        /**
         * Whether the discuss app is open or not. Useful to determine
         * whether the discuss or chat window logic should be applied.
         */
        __mfield_isOpen: attr({
            default: false,
        }),
        __mfield_isReplyingToMessage: attr({
            compute: '_computeIsReplyingToMessage',
            default: false,
            dependencies: [
                '__mfield_replyingToMessage',
            ],
        }),
        __mfield_isThreadPinned: attr({
            related: '__mfield_thread.__mfield_isPinned',
        }),
        /**
         * The menu_id of discuss app, received on mail/init_messaging and
         * used to open discuss from elsewhere.
         */
        __mfield_menu_id: attr({
            default: null,
        }),
        __mfield_messaging: one2one('mail.messaging', {
            inverse: '__mfield_discuss',
        }),
        __mfield_messagingInbox: many2one('mail.thread', {
            related: '__mfield_messaging.__mfield_inbox',
        }),
        __mfield_renamingThreads: one2many('mail.thread'),
        /**
         * The message that is currently selected as being replied to in Inbox.
         * There is only one reply composer shown at a time, which depends on
         * this selected message.
         */
        __mfield_replyingToMessage: many2one('mail.message', {
            compute: '_computeReplyingToMessage',
            dependencies: [
                '__mfield_isOpen',
                '__mfield_replyingToMessage',
            ],
        }),
        /**
         * The thread concerned by the reply feature in Inbox. It depends on the
         * message set to be replied, and should be considered read-only.
         */
        __mfield_replyingToMessageOriginThread: many2one('mail.thread', {
            related: '__mfield_replyingToMessage.__mfield_originThread',
        }),
        /**
         * The composer to display for the reply feature in Inbox. It depends
         * on the message set to be replied, and should be considered read-only.
         */
        __mfield_replyingToMessageOriginThreadComposer: one2one('mail.composer', {
            inverse: '__mfield_discussAsReplying',
            related: '__mfield_replyingToMessageOriginThread.__mfield_composer',
        }),
        /**
         * Quick search input value in the discuss sidebar (desktop). Useful
         * to filter channels and chats based on this input content.
         */
        __mfield_sidebarQuickSearchValue: attr({
            default: "",
        }),
        /**
         * Determines the domain to apply when fetching messages for `this.thread`.
         */
        __mfield_stringifiedDomain: attr({
            default: '[]',
        }),
        /**
         * Determines the `mail.thread` that should be displayed by `this`.
         */
        __mfield_thread: many2one('mail.thread', {
            compute: '_computeThread',
            dependencies: [
                '__mfield_activeMobileNavbarTabId',
                '__mfield_deviceIsMobile',
                '__mfield_isThreadPinned',
                '__mfield_messaging',
                '__mfield_messagingInbox',
                '__mfield_thread',
                '__mfield_threadModel',
            ],
        }),
        __mfield_threadId: attr({
            related: '__mfield_thread.__mfield_id',
        }),
        __mfield_threadModel: attr({
            related: '__mfield_thread.__mfield_model',
        }),
        /**
         * States the `mail.thread_view` displaying `this.thread`.
         */
        __mfield_threadView: one2one('mail.thread_view', {
            related: '__mfield_threadViewer.__mfield_threadView',
        }),
        /**
         * Determines the `mail.thread_viewer` managing the display of `this.thread`.
         */
        __mfield_threadViewer: one2one('mail.thread_viewer', {
            default: [['create']],
            inverse: '__mfield_discuss',
            isCausal: true,
        }),
    };

    Discuss.modelName = 'mail.discuss';

    return Discuss;
}

registerNewModel('mail.discuss', factory);

});
