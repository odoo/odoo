/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DiscussMobileMailboxSelectionItem extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {DiscussView}
     */
    get discussView() {
        return this.messaging && this.messaging.models['DiscussView'].get(this.props.discussViewLocalId);
    }

    /**
     * @returns {Thread}
     */
    get mailbox() {
        return this.messaging && this.messaging.models['Thread'].get(this.props.mailboxLocalId);
    }

}

Object.assign(DiscussMobileMailboxSelectionItem, {
    props: {
        discussViewLocalId: String,
        mailboxLocalId: String,
    },
    template: 'mail.DiscussMobileMailboxSelectionItem',
});

registerMessagingComponent(DiscussMobileMailboxSelectionItem);
