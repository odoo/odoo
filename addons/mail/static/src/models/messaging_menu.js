/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'MessagingMenu',
    lifecycleHooks: {
        _created() {
            document.addEventListener('click', this._onClickCaptureGlobal, true);
        },
        _willDelete() {
            document.removeEventListener('click', this._onClickCaptureGlobal, true);
        },
    },
    recordMethods: {
        /**
         * Close the messaging menu. Should reset its internal state.
         */
        close() {
            this.update({ isOpen: false });
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickDesktopTabButton(ev) {
            this.update({ activeTabId: ev.currentTarget.dataset.tabId });
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickNewMessage(ev) {
            if (!this.messaging.device.isSmall) {
                this.messaging.chatWindowManager.openNewMessage();
                this.close();
            } else {
                this.toggleMobileNewMessage();
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickToggler(ev) {
            // avoid following dummy href
            ev.preventDefault();
            if (!this.exists()) {
                return;
            }
            this.toggleOpen();
        },
        onHideMobileNewMessage() {
            this.update({ isMobileNewMessageToggled: false });
        },
        /**
         * @private
         * @param {Event} ev
         * @param {Object} ui
         * @param {Object} ui.item
         * @param {integer} ui.item.id
         */
        onMobileNewMessageInputSelect(ev, ui) {
            this.messaging.openChat({ partnerId: ui.item.id });
        },
        /**
         * @param {Object} req
         * @param {string} req.term
         * @param {function} res
         */
        onMobileNewMessageInputSource(req, res) {
            const value = _.escape(req.term);
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
        /**
         * Toggle the visibility of the messaging menu "new message" input in
         * mobile.
         */
        toggleMobileNewMessage() {
            this.update({ isMobileNewMessageToggled: !this.isMobileNewMessageToggled });
        },
        /**
         * Toggle whether the messaging menu is open or not.
         */
        toggleOpen() {
            this.update({ isOpen: !this.isOpen });
            this.messaging.refreshIsNotificationPermissionDefault();
            if (this.isOpen) {
                // populate some needaction messages on threads.
                this.messaging.inbox.thread.cache.update({ isCacheRefreshRequested: true });
            }
        },
        /**
         * @private
         * @returns {integer}
         */
        _computeCounter() {
            if (!this.messaging) {
                return 0;
            }
            const inboxCounter = this.messaging.inbox ? this.messaging.inbox.counter : 0;
            const unreadChannelsCounter = this.pinnedAndUnreadChannels.length;
            const notificationGroupsCounter = this.messaging.models['NotificationGroup'].all().reduce(
                (total, group) => total + group.notifications.length,
                0
            );
            const notificationPemissionCounter = this.messaging.isNotificationPermissionDefault ? 1 : 0;
            return inboxCounter + unreadChannelsCounter + notificationGroupsCounter + notificationPemissionCounter;
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
         _computeMobileMessagingNavbarView() {
            if (this.messaging.device && this.messaging.device.isSmall) {
                return {};
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMobileNewMessageAutocompleteInputView() {
            if (this.isOpen && this.messaging.isInitialized && this.messaging.device.isSmall && this.isMobileNewMessageToggled) {
                return {};
            }
            return clear();
        },
        /**
         * @private
         * @returns {string}
         */
        _computeMobileNewMessageInputPlaceholder() {
            return this.env._t("Search user...");
        },
        /**
         * @returns {FieldCommand}
         */
        _computeNotificationListView() {
            return this.isOpen ? {} : clear();
        },
        /**
         * @private
         * @returns {string}
         */
        _computeViewId() {
            return _.uniqueId('o_messagingMenu_');
        },
        /**
         * Closes the menu when clicking outside, if appropriate.
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onClickCaptureGlobal(ev) {
            if (!this.exists()) {
                return;
            }
            if (!this.component) {
                return;
            }
            // ignore click inside the menu
            if (!this.component.root.el || this.component.root.el.contains(ev.target)) {
                return;
            }
            // in all other cases: close the messaging menu when clicking outside
            this.close();
        },
    },
    fields: {
        /**
         * Tab selected in the messaging menu.
         * Either 'all', 'chat' or 'channel'.
         */
        activeTabId: attr({
            default: 'all',
        }),
        component: attr(),
        /**
         * States the counter of this messaging menu. The counter is an integer
         * value to give to the current user an estimate of how many things
         * (unread threads, notifications, ...) are yet to be processed by them.
         */
        counter: attr({
            compute: '_computeCounter',
        }),
        /**
         * Determine whether the mobile new message input is visible or not.
         */
        isMobileNewMessageToggled: attr({
            default: false,
        }),
        /**
         * Determine whether the messaging menu dropdown is open or not.
         */
        isOpen: attr({
            default: false,
        }),
        notificationListView: one('NotificationListView', {
            compute: '_computeNotificationListView',
            inverse: 'messagingMenuOwner',
        }),
        /**
         * The navbar view on the messaging menu when in mobile.
         */
        mobileMessagingNavbarView: one('MobileMessagingNavbarView', {
            compute: '_computeMobileMessagingNavbarView',
            inverse: 'messagingMenu',
        }),
        mobileNewMessageAutocompleteInputView: one('AutocompleteInputView', {
            compute: '_computeMobileNewMessageAutocompleteInputView',
            inverse: 'messagingMenuOwnerAsMobileNewMessageInput',
        }),
        mobileNewMessageInputPlaceholder: attr({
            compute: '_computeMobileNewMessageInputPlaceholder',
        }),
        /**
         * States all the pinned channels that have unread messages.
         */
        pinnedAndUnreadChannels: many('Thread', {
            inverse: 'messagingMenuAsPinnedAndUnreadChannel',
            readonly: true,
        }),
        /**
         * global JS generated ID for this record view. Useful to provide a
         * custom class to autocomplete input, so that click in an autocomplete
         * item is not considered as a click away from messaging menu in mobile.
         */
        viewId: attr({
            compute: '_computeViewId',
        }),
    },
});
