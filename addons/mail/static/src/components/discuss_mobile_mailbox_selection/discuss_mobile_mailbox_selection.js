/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class DiscussMobileMailboxSelection extends Component {

    /**
     * @returns {DiscussMobileMailboxSelectionView}
     */
    get discussMobileMailboxSelectionView() {
        return this.props.record;
    }

}

Object.assign(DiscussMobileMailboxSelection, {
    props: { record: Object },
    template: 'mail.DiscussMobileMailboxSelection',
});

registerMessagingComponent(DiscussMobileMailboxSelection);
