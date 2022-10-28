/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

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
