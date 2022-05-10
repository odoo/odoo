/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'DiscussView',
    identifyingFields: ['discuss'],
    recordMethods: {
        /**
         * Handles click on the mobile "new channel" button.
         *
         * @param {MouseEvent} ev
         */
        onClickMobileNewChannelButton(ev) {
            this.discuss.update({ isAddingChannel: true });
        },
        /**
         * Handles click on the mobile "new chat" button.
         *
         * @param {MouseEvent} ev
         */
        onClickMobileNewChatButton(ev) {
            this.discuss.update({ isAddingChat: true });
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
            this.discuss.clearIsAddingItem();
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
         * @param {Thread} mailbox
         */
        onClickMobileMailboxSelectionItem(mailbox) {
            if (!mailbox.exists()) {
                return;
            }
            mailbox.open();
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
            if (this.discuss.isAddingChannel) {
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
            if (this.discuss.isAddingChannel) {
                this.discuss.handleAddChannelAutocompleteSource(req, res);
            } else {
                this.discuss.handleAddChatAutocompleteSource(req, res);
            }
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMobileAddItemHeaderAutocompleteInputView() {
            if (
                this.messaging.device.isSmall &&
                (this.discuss.isAddingChannel || this.discuss.isAddingChat)
            ) {
                return insertAndReplace();
            }
            return clear();
        },
    },
    fields: {
        mobileAddItemHeaderAutocompleteInputView: one('AutocompleteInputView', {
            compute: '_computeMobileAddItemHeaderAutocompleteInputView',
            inverse: 'discussViewOwnerAsMobileAddItemHeader',
            isCausal: true,
        }),
        discuss: one('Discuss', {
            inverse: 'discussView',
            readonly: true,
            required: true,
        }),
        historyView: one('DiscussSidebarMailboxView', {
            default: insertAndReplace(),
            inverse: 'discussViewOwnerAsHistory',
            isCausal: true,
        }),
        inboxView: one('DiscussSidebarMailboxView', {
            default: insertAndReplace(),
            inverse: 'discussViewOwnerAsInbox',
            isCausal: true,
        }),
        /**
         * Reference of the quick search input. Useful to filter channels and
         * chats based on this input content.
         */
        quickSearchInputRef: attr(),
        starredView: one('DiscussSidebarMailboxView', {
            default: insertAndReplace(),
            inverse: 'discussViewOwnerAsStarred',
            isCausal: true,
        }),
    },
});
