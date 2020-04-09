odoo.define('mail.messaging.entity.MessagingMenu', function (require) {
'use strict';

const { registerNewEntity } = require('mail.messaging.entity.core');

function MessagingMenuFactory({ Entity }) {

    class MessagingMenu extends Entity {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Close the messaging menu. Should reset its internal state.
         */
        close() {
            this.update({
                activeTabId: 'all',
                isMobileNewMessageToggled: false,
                isOpen: false,
            });
        }

        /**
         * @param {string} activeTabId
         */
        setActiveTabId(activeTabId) {
            this.update({ activeTabId });
        }

        /**
         * Toggle the visibility of the messaging menu "new message" input in
         * mobile.
         */
        toggleMobileNewMessage() {
            this.update({
                isMobileNewMessageToggled: !this.isMobileNewMessageToggled,
            });
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
         * FIXME: using constructor so that patch is applied on class
         * instead of instance. This is necessary in order for patches
         * not affecting observable and incrementing rev number each
         * time a patched method is called.
         *
         * @static
         * @private
         * @returns {integer}
         */
        static _updateCounter() {
            const inboxMailbox = this.env.entities.Thread.mailboxFromId('inbox');
            return (
                this.env.entities.Thread.allUnreadChannels.length +
                (inboxMailbox ? inboxMailbox.counter : 0)
            );
        }

        /**
         * @override
         */
        _update(data) {
            const {
                /**
                 * Tab selected in the messaging menu.
                 * Either 'all', 'chat' or 'channel'.
                 */
                activeTabId = this.activeTabId || 'all',
                /**
                 * Determine whether the mobile new message input is visible or not.
                 */
                isMobileNewMessageToggled = this.isMobileNewMessageToggled || false,
                /**
                 * Determine whether the messaging menu dropdown is open or not.
                 */
                isOpen = this.isOpen || false,
            } = data;

            Object.assign(this, {
                activeTabId,
                /**
                 * FIXME: using static method so that patch is applied on class
                 * instead of instance. This is necessary in order for patches
                 * not affecting observable and incrementing rev number each
                 * time a patched method is called.
                 */
                counter: this.constructor._updateCounter(),
                isMobileNewMessageToggled,
                isOpen,
            });
        }

    }

    Object.assign(MessagingMenu, {
        relations: Object.assign({}, Entity.relations, {
            messaging: {
                inverse: 'messagingMenu',
                to: 'Messaging',
                type: 'one2one',
            },
        }),
    });

    return MessagingMenu;
}

registerNewEntity('MessagingMenu', MessagingMenuFactory);

});
