/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DiscussMobileMailboxSelectionItem extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {DiscussMobileMailboxSelectionItemView}
     */
    get discussMobileMailboxSelectionItemView() {
        return this.props.record;
    }

    /**
     * @returns {DiscussView}
     */
    get discussView() {
        return this.props.discussView;
    }

    /**
     * @returns {Mailbox}
     */
    get mailbox() {
        return this.props.mailbox;
    }

}

Object.assign(DiscussMobileMailboxSelectionItem, {
    props: {
        discussView: Object,
        mailbox: Object,
        record: Object,
    },
    template: 'mail.DiscussMobileMailboxSelectionItem',
});

registerMessagingComponent(DiscussMobileMailboxSelectionItem);
