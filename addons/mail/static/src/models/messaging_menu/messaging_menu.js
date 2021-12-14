/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one2many } from '@mail/model/model_field';

registerModel({
    name: 'MessagingMenu',
    identifyingFields: ['messaging'],
    recordMethods: {
        /**
         * Close the messaging menu. Should reset its internal state.
         */
        close() {
            this.update({ isOpen: false });
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
                this.messaging.inbox.cache.update({ isCacheRefreshRequested: true });
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
    },
    fields: {
        /**
         * Tab selected in the messaging menu.
         * Either 'all', 'chat' or 'channel'.
         */
        activeTabId: attr({
            default: 'all',
        }),
        /**
         * States the counter of this messaging menu. The counter is an integer
         * value to give to the current user an estimate of how many things
         * (unread threads, notifications, ...) are yet to be processed by him.
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
        /**
         * States all the pinned channels that have unread messages.
         */
         pinnedAndUnreadChannels: one2many('Thread', {
            inverse: 'messagingMenuAsPinnedAndUnreadChannel',
            readonly: true,
        }),
    },
});
