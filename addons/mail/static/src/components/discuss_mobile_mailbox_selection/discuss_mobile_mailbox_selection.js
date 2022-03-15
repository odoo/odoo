/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DiscussMobileMailboxSelection extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {Discuss}
     */
    get discuss() {
        return this.messaging && this.messaging.discuss;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when clicking on a mailbox selection item.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        const { mailboxLocalId } = ev.currentTarget.dataset;
        const mailbox = this.messaging.models['Thread'].get(mailboxLocalId);
        if (!mailbox) {
            return;
        }
        mailbox.open();
    }

}

Object.assign(DiscussMobileMailboxSelection, {
    props: {},
    template: 'mail.DiscussMobileMailboxSelection',
});

registerMessagingComponent(DiscussMobileMailboxSelection);
