/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DiscussMobileMailboxSelection extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {DiscussView}
     */
    get discussView() {
        return this.messaging && this.messaging.models['DiscussView'].get(this.props.localId);
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
    props: { localId: String },
    template: 'mail.DiscussMobileMailboxSelection',
});

registerMessagingComponent(DiscussMobileMailboxSelection);
