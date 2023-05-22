/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
import { escape, sprintf } from '@web/core/utils/strings';

registerModel({
    name: 'Discuss',
    recordMethods: {
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
            const name = this.discussView.addingChannelValue;
            this.discussView.clearIsAddingItem();
            if (ui.item.create) {
                const channel = await this.messaging.models['Thread'].performRpcCreateChannel({
                    name,
                    group_id: this.messaging.internalUserGroupId,
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
            this.discussView.update({ addingChannelValue: req.term });
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
                create: true,
                escapedValue,
                label: sprintf(
                    `<strong>${this.env._t('Create %s')}</strong>`,
                    `<em><span class="fa fa-hashtag"/>${escapedValue}</em>`,
                ),
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
            this.discussView.clearIsAddingItem();
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
            this.update({ discussView: {} });
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
                        name: this.env._t("Discuss"),
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
    },
    fields: {
        activeId: attr({
            compute() {
                if (!this.activeThread) {
                    return clear();
                }
                return this.threadToActiveId(this.activeThread);
            },
        }),
        /**
         * Active mobile navbar tab, either 'mailbox', 'chat', or 'channel'.
         */
        activeMobileNavbarTabId: attr({
            default: 'mailbox',
        }),
        /**
         * Determines the `Thread` that should be displayed by `this`.
         */
        activeThread: one('Thread', {
            /**
             * Only mailboxes and pinned channels are allowed in Discuss.
             */
            compute() {
                if (!this.thread) {
                    return clear();
                }
                if (this.thread.channel && this.thread.isPinned) {
                    return this.thread;
                }
                if (this.thread.mailbox) {
                    return this.thread;
                }
                return clear();
            },
        }),
        addChannelInputPlaceholder: attr({
            compute() {
                return this.env._t("Create or search channel...");
            },
        }),
        addChatInputPlaceholder: attr({
            compute() {
                return this.env._t("Search user...");
            },
        }),
        /**
         * Discuss sidebar category for `channel` type channel threads.
         */
        categoryChannel: one('DiscussSidebarCategory', {
            default: {},
            inverse: 'discussAsChannel',
        }),
        /**
         * Discuss sidebar category for `chat` type channel threads.
         */
        categoryChat: one('DiscussSidebarCategory', {
            default: {},
            inverse: 'discussAsChat',
        }),
        discussView: one('DiscussView', {
            inverse: 'discuss',
        }),
        /**
         * Determines whether `this.thread` should be displayed.
         */
        hasThreadView: attr({
            compute() {
                if (!this.activeThread || !this.discussView) {
                    return false;
                }
                if (
                    this.messaging.device.isSmall &&
                    (
                        this.activeMobileNavbarTabId !== 'mailbox' ||
                        !this.activeThread.mailbox
                    )
                ) {
                    return false;
                }
                return true;
            },
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
            compute() {
                return (this.messaging.device.isSmall && this.activeMobileNavbarTabId !== 'mailbox') ? {} : clear();
            },
            inverse: 'discussOwner',
        }),
        /**
         * The navbar view on the discuss app when in mobile and when not
         * replying to a message from inbox.
         */
        mobileMessagingNavbarView: one('MobileMessagingNavbarView', {
            compute() {
                if (
                    this.messaging.device &&
                    this.messaging.device.isSmall &&
                    !(this.threadView && this.threadView.replyingToMessageView)
                ) {
                    return {};
                }
                return clear();
            },
            inverse: 'discuss',
        }),
        /**
         * Quick search input value in the discuss sidebar (desktop). Useful
         * to filter channels and chats based on this input content.
         */
        sidebarQuickSearchValue: attr({
            default: "",
        }),
        thread: one('Thread'),
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
            compute() {
                return {
                    hasMemberList: true,
                    hasThreadView: this.hasThreadView,
                    hasTopbar: true,
                    thread: this.activeThread ? this.activeThread : clear(),
                };
            },
            inverse: 'discuss',
            required: true,
        }),
    },
});
