/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'DiscussView',
    recordMethods: {
        clearIsAddingItem() {
            this.update({
                addingChannelValue: clear(),
                isAddingChannel: clear(),
                isAddingChat: clear(),
            });
        },
        /**
         * Handles click on the mobile "new channel" button.
         *
         * @param {MouseEvent} ev
         */
        onClickMobileNewChannelButton(ev) {
            this.update({ isAddingChannel: true });
        },
        /**
         * Handles click on the mobile "new chat" button.
         *
         * @param {MouseEvent} ev
         */
        onClickMobileNewChatButton(ev) {
            this.update({ isAddingChat: true });
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
            if (!meetingChannel.exists() || !this.discuss.threadView) {
                return;
            }
            this.discuss.threadView.topbar.openInvitePopoverView();
        },
        onHideMobileAddItemHeader() {
            if (!this.exists()) {
                return;
            }
            this.clearIsAddingItem();
        },
        /**
         * @param {KeyboardEvent} ev
         */
        onInputQuickSearch(ev) {
            ev.stopPropagation();
            this.discuss.onInputQuickSearch(this.quickSearchInputRef.el.value);
        },
        /**
         * Called when clicking on a mailbox selection item.
         *
         * @param {Mailbox} mailbox
         */
        onClickMobileMailboxSelectionItem(mailbox) {
            if (!mailbox.exists()) {
                return;
            }
            mailbox.thread.open();
        },
        /**
         * @param {Event} ev
         * @param {Object} ui
         * @param {Object} ui.item
         * @param {integer} ui.item.id
         */
        onMobileAddItemHeaderInputSelect(ev, ui) {
            if (!this.exists()) {
                return;
            }
            if (this.isAddingChannel) {
                this.discuss.handleAddChannelAutocompleteSelect(ev, ui);
            } else {
                this.discuss.handleAddChatAutocompleteSelect(ev, ui);
            }
        },
        /**
         * @param {Object} req
         * @param {string} req.term
         * @param {function} res
         */
        onMobileAddItemHeaderInputSource(req, res) {
            if (!this.exists()) {
                return;
            }
            if (this.isAddingChannel) {
                this.discuss.handleAddChannelAutocompleteSource(req, res);
            } else {
                this.discuss.handleAddChatAutocompleteSource(req, res);
            }
        },
        /**
         * @private
         */
        _onDiscussActiveThreadChanged() {
            this.env.services.router.pushState({
                action: this.discuss.discussView.actionId,
                active_id: this.discuss.activeId,
            });
        },
    },
    fields: {
        /**
         * Used to push state when changing active thread.
         * The id of the action which opened discuss.
         */
        actionId: attr(),
        /**
         * Value that is used to create a channel from the sidebar.
         */
        addingChannelValue: attr({
            default: "",
        }),
        discuss: one('Discuss', {
            identifying: true,
            inverse: 'discussView',
        }),
        historyView: one('DiscussSidebarMailboxView', {
            default: {},
            inverse: 'discussViewOwnerAsHistory',
        }),
        inboxView: one('DiscussSidebarMailboxView', {
            default: {},
            inverse: 'discussViewOwnerAsInbox',
        }),
        /**
         * Determines whether current user is adding a channel from the sidebar.
         */
        isAddingChannel: attr({
            default: false,
        }),
        /**
         * Determines whether current user is adding a chat from the sidebar.
         */
        isAddingChat: attr({
            default: false,
        }),
        mobileAddItemHeaderAutocompleteInputView: one('AutocompleteInputView', {
            compute() {
                if (
                    this.messaging.device.isSmall &&
                    (this.isAddingChannel || this.isAddingChat)
                ) {
                    return {};
                }
                return clear();
            },
            inverse: 'discussViewOwnerAsMobileAddItemHeader',
        }),
        orderedMailboxes: many('Mailbox', {
            related: 'messaging.allMailboxes',
            sort: [['smaller-first', 'sequence']],
        }),
        /**
         * Reference of the quick search input. Useful to filter channels and
         * chats based on this input content.
         */
        quickSearchInputRef: attr(),
        starredView: one('DiscussSidebarMailboxView', {
            default: {},
            inverse: 'discussViewOwnerAsStarred',
        }),
    },
    onChanges: [
        {
            dependencies: ['discuss.activeThread'],
            methodName: '_onDiscussActiveThreadChanged',
        },
    ],
});
