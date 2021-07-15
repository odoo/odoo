odoo.define('mail/static/src/models/messaging_menu/messaging_menu.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, one2one } = require('mail/static/src/model/model_field.js');

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
        _updateCounter() {
            if (!this.env.messaging) {
                return 0;
            }
            const inboxMailbox = this.env.messaging.inbox;
            const unreadChannels = this.env.models['mail.thread'].all(thread =>
                thread.localMessageUnreadCounter > 0 &&
                thread.model === 'mail.channel' &&
                thread.isPinned
            );
            let counter = unreadChannels.length;
            if (inboxMailbox) {
                counter += inboxMailbox.counter;
            }
            if (this.messaging.notificationGroupManager) {
                counter += this.messaging.notificationGroupManager.groups.reduce(
                    (total, group) => total + group.notifications.length,
                    0
                );
            }
            if (this.messaging.isNotificationPermissionDefault()) {
                counter++;
            }
            return counter;
        }

        /**
         * @override
         */
        _updateAfter(previous) {
            const counter = this._updateCounter();
            if (this.counter !== counter) {
                this.update({ counter });
            }
        }

    }

    MessagingMenu.fields = {
        /**
         * Tab selected in the messaging menu.
         * Either 'all', 'chat' or 'channel'.
         */
        activeTabId: attr({
            default: 'all',
        }),
        counter: attr({
            default: 0,
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
        messaging: one2one('mail.messaging', {
            inverse: 'messagingMenu',
        }),
        messagingInbox: one2one('mail.thread', {
            related: 'messaging.inbox',
        }),
        messagingInboxMainCache: one2one('mail.thread_cache', {
            related: 'messagingInbox.mainCache',
        }),
    };

    MessagingMenu.modelName = 'mail.messaging_menu';

    return MessagingMenu;
}

registerNewModel('mail.messaging_menu', factory);

});
