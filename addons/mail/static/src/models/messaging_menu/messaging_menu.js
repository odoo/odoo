/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2many, one2one } from '@mail/model/model_field';

function factory(dependencies) {

    class MessagingMenu extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Close the messaging menu. Should reset its internal state.
         */
        close() {
            this.update({ isOpen: false });
        }

        /**
         * Toggle the visibility of the messaging menu "new message" input in
         * mobile.
         */
        toggleMobileNewMessage() {
            this.update({ isMobileNewMessageToggled: !this.isMobileNewMessageToggled });
        }

        /**
         * Toggle whether the messaging menu is open or not.
         */
        toggleOpen() {
            this.update({ isOpen: !this.isOpen });
            this.env.messaging.refreshIsNotificationPermissionDefault();
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         */
        _computeInboxMessagesAutoloader() {
            if (!this.isOpen) {
                return;
            }
            const inbox = this.env.messaging.inbox;
            if (!inbox || !inbox.mainCache) {
                return;
            }
            // populate some needaction messages on threads.
            inbox.mainCache.update({ isCacheRefreshRequested: true });
        }

        /**
         * @private
         * @returns {integer}
         */
        _computeCounter() {
            if (!this.env.messaging) {
                return 0;
            }
            const inboxCounter = this.env.messaging.inbox ? this.env.messaging.inbox.counter : 0;
            const unreadChannelsCounter = this.env.messaging.allPinnedChannels.filter(
                channel => channel.localMessageUnreadCounter > 0
            ).length;
            const notificationGroupsCounter = this.messaging.notificationGroupManager
                ? this.messaging.notificationGroupManager.groups.reduce(
                    (total, group) => total + group.notifications.length,
                    0
                )
                : 0;
            const notificationPemissionCounter = this.messaging.isNotificationPermissionDefault ? 1 : 0;
            return inboxCounter + unreadChannelsCounter + notificationGroupsCounter + notificationPemissionCounter;
        }

    }

    MessagingMenu.fields = {
        /**
         * Serves as compute dependency.
         */
        allPinnedChannels: one2many('mail.thread', {
            related: 'messaging.allPinnedChannels',
        }),
        /**
         * Serves as compute dependency.
         */
        allPinnedChannelsLocalMessageUnreadCounter: attr({
            related: 'allPinnedChannels.localMessageUnreadCounter',
        }),
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
            dependencies: [
                'allPinnedChannels',
                'allPinnedChannelsLocalMessageUnreadCounter',
                'messaging',
                'messagingInbox',
                'messagingInboxCounter',
                'messagingIsNotificationPermissionDefault',
                'messagingNotificationGroupManager',
                'messagingNotificationGroupManagerGroups',
                'messagingNotificationGroupManagerGroupsNotifications',
            ],
        }),
        /**
         * Dummy field to automatically load messages of inbox when messaging
         * menu is open.
         *
         * Useful because needaction notifications require fetching inbox
         * messages to work.
         */
        inboxMessagesAutoloader: attr({
            compute: '_computeInboxMessagesAutoloader',
            dependencies: [
                'isOpen',
                'messagingInbox',
                'messagingInboxMainCache',
            ],
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
         * Serves as compute dependency.
         */
        messaging: one2one('mail.messaging', {
            inverse: 'messagingMenu',
        }),
        /**
         * Serves as compute dependency.
         */
        messagingInbox: one2one('mail.thread', {
            related: 'messaging.inbox',
        }),
        /**
         * Serves as compute dependency.
         */
        messagingInboxCounter: attr({
            related: 'messagingInbox.counter',
        }),
        /**
         * Serves as compute dependency.
         */
        messagingIsNotificationPermissionDefault: attr({
            related: 'messaging.isNotificationPermissionDefault',
        }),
        /**
         * Serves as compute dependency.
         */
        messagingInboxMainCache: one2one('mail.thread_cache', {
            related: 'messagingInbox.mainCache',
        }),
        /**
         * Serves as compute dependency.
         */
        messagingNotificationGroupManager: one2one('mail.notification_group_manager', {
            related: 'messaging.notificationGroupManager',
        }),
        /**
         * Serves as compute dependency.
         */
        messagingNotificationGroupManagerGroups: one2many('mail.notification_group', {
            related: 'messagingNotificationGroupManager.groups'
        }),
        /**
         * Serves as compute dependency.
         */
        messagingNotificationGroupManagerGroupsNotifications: one2many('mail.notification', {
            related: 'messagingNotificationGroupManagerGroups.notifications'
        }),
    };

    MessagingMenu.modelName = 'mail.messaging_menu';

    return MessagingMenu;
}

registerNewModel('mail.messaging_menu', factory);
