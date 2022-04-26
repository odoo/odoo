/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';

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
        /**
         * Handles OWL update on the discuss component.
         */
        onComponentUpdate() {
            if (this.discuss.thread) {
                if (this.lastPushStateActiveThread !== this.discuss.thread) {
                    this.env.services.router.pushState({
                        action: this.actionId,
                        active_id: this.discuss.activeId,
                    });
                    this.update({
                        lastPushStateActiveThread: replace(this.discuss.thread),
                    });
                }
            }
            if (
                this.discuss.thread &&
                this.discuss.thread === this.messaging.inbox &&
                this.discuss.threadView &&
                this.lastThreadCache && this.lastThreadCache.localId === this.discuss.threadView.threadCache.localId &&
                this.lastThreadCounter > 0 && this.discuss.thread.counter === 0
            ) {
                this.env.services.effect.add({
                    message: this.env._t("Congratulations, your inbox is empty!"),
                    type: 'rainbow_man',
                });
            }
            const lastThreadCache = (
                this.discuss.threadView &&
                this.discuss.threadView.threadCache &&
                this.discuss.threadView.threadCache
            );
            this.update({
                lastThreadCache: lastThreadCache ? replace(lastThreadCache) : clear(),
                lastThreadCounter: (
                    this.discuss.thread &&
                    this.discuss.thread.counter
                ),
            });
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
        /**
         * Used to push state when changing active thread.
         * The id of the action which opened discuss.
         */
        actionId: attr(),
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
        lastPushStateActiveThread: one('Thread'),
        /**
         * Useful to display rainbow man on inbox.
         */
        lastThreadCache: one('ThreadCache'),
        /**
         * Useful to display rainbow man on inbox.
         */
        lastThreadCounter: attr(),
        mobileAddItemHeaderAutocompleteInputView: one('AutocompleteInputView', {
            compute: '_computeMobileAddItemHeaderAutocompleteInputView',
            inverse: 'discussViewOwnerAsMobileAddItemHeader',
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
