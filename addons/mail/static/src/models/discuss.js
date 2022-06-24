/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';
import { escape, sprintf } from '@web/core/utils/strings';

registerModel({
    name: 'Discuss',
    recordMethods: {
        clearIsAddingItem() {
            this.update({
                addingChannelValue: "",
                isAddingChannel: false,
                isAddingChat: false,
            });
        },
        /**
         * Close the discuss app. Should reset its internal state.
         */
        close() {
            this.update({ discussView: clear() });
        },
        focus() {
            if (this.threadView && this.threadView.composerView) {
                this.threadView.composerView.update({ doFocus: true });
            }
        },
        /**
         * @param {Event} ev
         * @param {Object} ui
         * @param {Object} ui.item
         * @param {integer} ui.item.id
         */
        async handleAddChannelAutocompleteSelect(ev, ui) {
            // Necessary in order to prevent AutocompleteSelect event's default
            // behaviour as html tags visible for a split second in text area
            ev.preventDefault();
            const name = this.addingChannelValue;
            this.clearIsAddingItem();
            if (ui.item.special) {
                const channel = await this.messaging.models['Thread'].performRpcCreateChannel({
                    name,
                    privacy: ui.item.special === 'private' ? 'private' : 'groups',
                });
                channel.open();
            } else {
                const channel = this.messaging.models['Thread'].insert({
                    id: ui.item.id,
                    model: 'mail.channel',
                });
                await channel.join();
                // Channel must be pinned immediately to be able to open it before
                // the result of join is received on the bus.
                channel.update({ isServerPinned: true });
                channel.open();
            }
        },
        /**
         * @param {Object} req
         * @param {string} req.term
         * @param {function} res
         */
        async handleAddChannelAutocompleteSource(req, res) {
            this.update({ addingChannelValue: req.term });
            const threads = await this.messaging.models['Thread'].searchChannelsToOpen({ limit: 10, searchTerm: req.term });
            const items = threads.map((thread) => {
                const escapedName = escape(thread.name);
                return {
                    id: thread.id,
                    label: escapedName,
                    value: escapedName,
                };
            });
            const escapedValue = escape(req.term);
            // XDU FIXME could use a component but be careful with owl's
            // renderToString https://github.com/odoo/owl/issues/708
            items.push({
                label: sprintf(
                    `<strong>${this.env._t('Create %s')}</strong>`,
                    `<em><span class="fa fa-hashtag"/>${escapedValue}</em>`,
                ),
                escapedValue,
                special: 'public'
            }, {
                label: sprintf(
                    `<strong>${this.env._t('Create %s')}</strong>`,
                    `<em><span class="fa fa-lock"/>${escapedValue}</em>`,
                ),
                escapedValue,
                special: 'private'
            });
            res(items);
        },
        /**
         * @param {Event} ev
         * @param {Object} ui
         * @param {Object} ui.item
         * @param {integer} ui.item.id
         */
        handleAddChatAutocompleteSelect(ev, ui) {
            this.messaging.openChat({ partnerId: ui.item.id });
            this.clearIsAddingItem();
        },
        /**
         * @param {Object} req
         * @param {string} req.term
         * @param {function} res
         */
        handleAddChatAutocompleteSource(req, res) {
            const value = escape(req.term);
            this.messaging.models['Partner'].imSearch({
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
        },
        open() {
            this.update({ discussView: insertAndReplace() });
        },
        /**
         * Opens thread from init active id if the thread exists.
         */
        openInitThread() {
            const [model, id] = typeof this.initActiveId === 'number'
                ? ['mail.channel', this.initActiveId]
                : this.initActiveId.split('_');
            const thread = this.messaging.models['Thread'].findFromIdentifyingData({
                id: model !== 'mail.box' ? Number(id) : id,
                model,
            });
            if (!thread) {
                return;
            }
            thread.open();
            if (this.messaging.device.isSmall && thread.channel && thread.channel.channel_type) {
                this.update({ activeMobileNavbarTabId: thread.channel.channel_type });
            }
        },
        /**
         * Opens the given thread in Discuss, and opens Discuss if necessary.
         *
         * @param {Thread} thread
         * @param {Object} [param1={}]
         * @param {Boolean} [param1.focus]
         */
        async openThread(thread, { focus } = {}) {
            this.update({ thread });
            if (focus !== undefined ? focus : !this.messaging.device.isMobileDevice) {
                this.focus();
            }
            if (!this.discussView) {
                this.env.services.action.doAction(
                    'mail.action_discuss',
                    {
                        active_id: this.threadToActiveId(this),
                        clearBreadcrumbs: false,
                        on_reverse_breadcrumb: () => this.close(), // this is useless, close is called by destroy anyway
                    },
                );
            }
        },
        /**
         * @param {Thread} thread
         * @returns {string}
         */
        threadToActiveId(thread) {
            return `${thread.model}_${thread.id}`;
        },
        /**
         * @param {string} value
         */
        onInputQuickSearch(value) {
            // Opens all categories only when user starts to search from empty search value.
            if (!this.sidebarQuickSearchValue) {
                this.categoryChat.open();
                this.categoryChannel.open();
            }
            this.update({ sidebarQuickSearchValue: value });
        },
        /**
         * @private
         * @returns {string|undefined}
         */
        _computeActiveId() {
            if (!this.thread) {
                return clear();
            }
            return this.threadToActiveId(this.thread);
        },
        /**
         * @private
         * @returns {string}
         */
        _computeAddChannelInputPlaceholder() {
            return this.env._t("Create or search channel...");
        },
        /**
         * @private
         * @returns {string}
         */
        _computeAddChatInputPlaceholder() {
            return this.env._t("Search user...");
        },
        /**
         * @private
         * @returns {string}
         */
        _computeAddingChannelValue() {
            if (!this.discussView) {
                return "";
            }
            return this.addingChannelValue;
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasThreadView() {
            if (!this.thread || !this.discussView) {
                return false;
            }
            if (
                this.messaging.device.isSmall &&
                (
                    this.activeMobileNavbarTabId !== 'mailbox' ||
                    !this.thread.mailbox
                )
            ) {
                return false;
            }
            return true;
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsAddingChannel() {
            if (!this.discussView) {
                return false;
            }
            return this.isAddingChannel;
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsAddingChat() {
            if (!this.discussView) {
                return false;
            }
            return this.isAddingChat;
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMobileMessagingNavbarView() {
            if (
                this.messaging.device &&
                this.messaging.device.isSmall &&
                !(this.threadView && this.threadView.replyingToMessageView)
            ) {
                return insertAndReplace();
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeNotificationListView() {
            return (this.messaging.device.isSmall && this.activeMobileNavbarTabId !== 'mailbox') ? insertAndReplace() : clear();
        },
        /**
         * Only mailboxes and pinned channels are allowed in Discuss.
         *
         * @private
         * @returns {FieldCommand|undefined}
         */
        _computeThread() {
            if (!this.thread) {
                return clear();
            }
            if (this.thread.channel && this.thread.isPinned) {
                return undefined;
            }
            if (this.thread.mailbox) {
                return undefined;
            }
            return clear();
        },
        /**
         * @private
         * @returns {ThreadViewer}
         */
        _computeThreadViewer() {
            return insertAndReplace({
                hasMemberList: true,
                hasThreadView: this.hasThreadView,
                hasTopbar: true,
                thread: this.thread ? this.thread : clear(),
            });
        },
    },
    fields: {
        activeId: attr({
            compute: '_computeActiveId',
        }),
        /**
         * Active mobile navbar tab, either 'mailbox', 'chat', or 'channel'.
         */
        activeMobileNavbarTabId: attr({
            default: 'mailbox',
        }),
        addChannelInputPlaceholder: attr({
            compute: '_computeAddChannelInputPlaceholder',
        }),
        addChatInputPlaceholder: attr({
            compute: '_computeAddChatInputPlaceholder',
        }),
        /**
         * Value that is used to create a channel from the sidebar.
         */
        addingChannelValue: attr({
            compute: '_computeAddingChannelValue',
            default: "",
        }),
        /**
         * Discuss sidebar category for `channel` type channel threads.
         */
        categoryChannel: one('DiscussSidebarCategory', {
            default: insertAndReplace(),
            inverse: 'discussAsChannel',
            isCausal: true,
        }),
        /**
         * Discuss sidebar category for `chat` type channel threads.
         */
        categoryChat: one('DiscussSidebarCategory', {
            default: insertAndReplace(),
            inverse: 'discussAsChat',
            isCausal: true,
        }),
        discussView: one('DiscussView', {
            inverse: 'discuss',
            isCausal: true,
        }),
        /**
         * Determines whether `this.thread` should be displayed.
         */
        hasThreadView: attr({
            compute: '_computeHasThreadView',
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
        }),
        /**
         * Determine whether current user is currently adding a chat from
         * the sidebar.
         */
        isAddingChat: attr({
            compute: '_computeIsAddingChat',
            default: false,
        }),
        /**
         * Determines if the logic for opening a thread via the `initActiveId`
         * has been processed. This is necessary to ensure that this only
         * happens once.
         */
        isInitThreadHandled: attr({
            default: false,
        }),
        /**
         * The menu_id of discuss app, received on mail/init_messaging and
         * used to open discuss from elsewhere.
         */
        menu_id: attr({
            default: null,
        }),
        notificationListView: one('NotificationListView', {
            compute: '_computeNotificationListView',
            inverse: 'discussOwner',
            isCausal: true,
        }),
        /**
         * The navbar view on the discuss app when in mobile and when not
         * replying to a message from inbox.
         */
        mobileMessagingNavbarView: one('MobileMessagingNavbarView', {
            compute: '_computeMobileMessagingNavbarView',
            inverse: 'discuss',
            isCausal: true,
        }),
        /**
         * Quick search input value in the discuss sidebar (desktop). Useful
         * to filter channels and chats based on this input content.
         */
        sidebarQuickSearchValue: attr({
            default: "",
        }),
        /**
         * Determines the `Thread` that should be displayed by `this`.
         */
        thread: one('Thread', {
            compute: '_computeThread',
        }),
        /**
         * States the `ThreadView` displaying `this.thread`.
         */
        threadView: one('ThreadView', {
            related: 'threadViewer.threadView',
        }),
        /**
         * Determines the `ThreadViewer` managing the display of `this.thread`.
         */
        threadViewer: one('ThreadViewer', {
            compute: '_computeThreadViewer',
            inverse: 'discuss',
            isCausal: true,
            readonly: true,
            required: true,
        }),
    },
});
