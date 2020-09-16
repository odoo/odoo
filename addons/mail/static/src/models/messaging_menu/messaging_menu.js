odoo.define('mail/static/src/models/messaging_menu/messaging_menu.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, one2one } = require('mail/static/src/model/model_field_utils.js');

function factory(dependencies) {

    class MessagingMenu extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Close the messaging menu. Should reset its internal state.
         */
        close() {
            this.update({
                __mfield_activeTabId: 'all',
                __mfield_isMobileNewMessageToggled: false,
                __mfield_isOpen: false,
            });
        }

        /**
         * Toggle the visibility of the messaging menu "new message" input in
         * mobile.
         */
        toggleMobileNewMessage() {
            this.update({
                __mfield_isMobileNewMessageToggled: !this.__mfield_isMobileNewMessageToggled(this),
            });
        }

        /**
         * Toggle whether the messaging menu is open or not.
         */
        toggleOpen() {
            this.update({
                __mfield_isOpen: !this.__mfield_isOpen(this),
            });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         */
        _computeInboxMessagesAutoloader() {
            if (!this.__mfield_isOpen(this)) {
                return;
            }
            const inbox = this.env.messaging.__mfield_inbox(this);
            if (
                !inbox ||
                !inbox.__mfield_mainCache(this) ||
                inbox.__mfield_mainCache(this).__mfield_isLoaded(this) ||
                inbox.__mfield_mainCache(this).__mfield_isLoading(this)
            ) {
                return;
            }
            // populate some needaction messages on threads.
            inbox.__mfield_mainCache(this).update({
                __mfield_hasToLoadMessages: true,
            });
        }

        /**
         * @private
         * @returns {integer}
         */
        _updateCounter() {
            if (!this.env.messaging) {
                return 0;
            }
            const inboxMailbox = this.env.messaging.__mfield_inbox(this);
            const unreadChannels = this.env.models['mail.thread'].all(thread =>
                thread.__mfield_localMessageUnreadCounter(this) > 0 &&
                thread.__mfield_model(this) === 'mail.channel'
            );
            let counter = unreadChannels.length;
            if (inboxMailbox) {
                counter += inboxMailbox.__mfield_counter(this);
            }
            if (!this.__mfield_messaging(this)) {
                // compute after delete
                return counter;
            }
            if (this.__mfield_messaging(this).__mfield_notificationGroupManager(this)) {
                counter += this.__mfield_messaging(this).__mfield_notificationGroupManager(this).__mfield_groups(this).reduce(
                    (total, group) => total + group.__mfield_notifications(this).length,
                    0
                );
            }
            return counter;
        }

        /**
         * @override
         */
        _updateAfter(previous) {
            const counter = this._updateCounter();
            if (this.__mfield_counter(this) !== counter) {
                this.update({
                    __mfield_counter: counter,
                });
            }
        }

    }

    MessagingMenu.fields = {
        /**
         * Tab selected in the messaging menu.
         * Either 'all', 'chat' or 'channel'.
         */
        __mfield_activeTabId: attr({
            default: 'all',
        }),
        __mfield_counter: attr({
            default: 0,
        }),
        /**
         * Dummy field to automatically load messages of inbox when messaging
         * menu is open.
         *
         * Useful because needaction notifications require fetching inbox
         * messages to work.
         */
        __mfield_inboxMessagesAutoloader: attr({
            compute: '_computeInboxMessagesAutoloader',
            dependencies: [
                '__mfield_isOpen',
                '__mfield_messagingInbox',
                '__mfield_messagingInboxMainCache',
                '__mfield_messagingInboxMainCacheIsLoaded',
                '__mfield_messagingInboxMainCacheIsLoading',
            ],
        }),
        /**
         * Determine whether the mobile new message input is visible or not.
         */
        __mfield_isMobileNewMessageToggled: attr({
            default: false,
        }),
        /**
         * Determine whether the messaging menu dropdown is open or not.
         */
        __mfield_isOpen: attr({
            default: false,
        }),
        __mfield_messaging: one2one('mail.messaging', {
            inverse: '__mfield_messagingMenu',
        }),
        __mfield_messagingInbox: one2one('mail.thread', {
            related: '__mfield_messaging.__mfield_inbox',
        }),
        __mfield_messagingInboxMainCache: one2one('mail.thread_cache', {
            related: '__mfield_messagingInbox.__mfield_mainCache',
        }),
        __mfield_messagingInboxMainCacheIsLoaded: attr({
            related: '__mfield_messagingInboxMainCache.__mfield_isLoaded',
        }),
        __mfield_messagingInboxMainCacheIsLoading: attr({
            related: '__mfield_messagingInboxMainCache.__mfield_isLoading',
        }),
    };

    MessagingMenu.modelName = 'mail.messaging_menu';

    return MessagingMenu;
}

registerNewModel('mail.messaging_menu', factory);

});
