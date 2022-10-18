/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DiscussMobileMailboxSelectionItem extends Component {

    /**
     * @returns {DiscussMobileMailboxSelectionItemView}
     */
    get discussMobileMailboxSelectionItemView() {
        return this.props.record;
    }

}

Object.assign(DiscussMobileMailboxSelectionItem, {
    props: { record: Object },
    template: 'mail.DiscussMobileMailboxSelectionItem',
});

registerMessagingComponent(DiscussMobileMailboxSelectionItem);
