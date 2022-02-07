/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace, link, unlink } from '@mail/model/model_field_command';

registerModel({
    name: 'Discuss',
    identifyingFields: ['messaging'],
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
         * Handles click on the mobile "new chat" button.
         *
         * @param {MouseEvent} ev
         */
        onClickMobileNewChatButton(ev) {
            this.discussView.update({
                mobileAddChatInputView: this.discussView.mobileAddChatInputView ? clear() : insertAndReplace({ doFocus: true }),
            });
        },
        /**
         * Handles click on the mobile "new channel" button.
         *
         * @param {MouseEvent} ev
         */
        onClickMobileNewChannelButton(ev) {
            this.discussView.update({
                mobileAddChannelInputView: this.discussView.mobileAddChannelInputView ? clear() : insertAndReplace({ doFocus: true }),
            });
        },
        /**
         * Handles click on the "Start a meeting" button.
         *
         * @param {MouseEvent} ev
         */
        async onClickStartAMeetingButton(ev) {
            const meetingChannel = await this.messaging.models['Thread'].createGroupChat({
                default_display_mode: 'video_full_screen',
                partners_to: [this.messaging.currentPartner.id],
            });
            meetingChannel.toggleCall({ startWithVideo: true });
            await meetingChannel.open({ focus: false });
            if (!meetingChannel.exists() || !this.threadView) {
                return;
            }
            this.threadView.topbar.openInvitePopoverView();
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
            if (this.messaging.device.isMobile && thread.channel_type) {
                this.update({ activeMobileNavbarTabId: thread.channel_type });
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
            this.update({
                thread: link(thread),
            });
            if (focus !== undefined ? focus : !this.messaging.device.isMobileDevice) {
                this.focus();
            }
            if (!this.discussView) {
                this.env.bus.trigger('do-action', {
                    action: 'mail.action_discuss',
                    options: {
                        active_id: this.threadToActiveId(this),
                        clear_breadcrumbs: false,
                        on_reverse_breadcrumb: () => this.close(), // this is useless, close is called by destroy anyway
                    },
                });
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
         * @returns {boolean}
         */
        _computeHasThreadView() {
            if (!this.thread || !this.discussView) {
                return false;
            }
            if (
                this.messaging.device.isMobile &&
                (
                    this.activeMobileNavbarTabId !== 'mailbox' ||
                    this.thread.model !== 'mail.box'
                )
            ) {
                return false;
            }
            return true;
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMobileMessagingNavbarView() {
            if (
                this.messaging.device &&
                this.messaging.device.isMobile &&
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
            return (this.messaging.device.isMobile && this.activeMobileNavbarTabId !== 'mailbox') ? insertAndReplace() : clear();
        },
        /**
         * Only pinned threads are allowed in discuss.
         *
         * @private
         * @returns {Thread|undefined}
         */
        _computeThread() {
            if (!this.thread || !this.thread.isPinned) {
                return unlink();
            }
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
                thread: this.thread ? link(this.thread) : unlink(),
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
        /**
         * Discuss sidebar category for `channel` type channel threads.
         */
        categoryChannel: one('DiscussSidebarCategory', {
            inverse: 'discussAsChannel',
            isCausal: true,
        }),
        /**
         * Discuss sidebar category for `chat` type channel threads.
         */
        categoryChat: one('DiscussSidebarCategory', {
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
