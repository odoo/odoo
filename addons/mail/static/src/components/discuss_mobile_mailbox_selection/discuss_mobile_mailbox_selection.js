/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DiscussMobileMailboxSelectionView extends Component {

    /**
     * @returns {DiscussMobileMailboxSelectionView}
     */
    get discussMobileMailboxSelectionView() {
        return this.props.record;
    }

}

Object.assign(DiscussMobileMailboxSelectionView, {
    props: { record: Object },
    template: 'mail.DiscussMobileMailboxSelectionView',
});

registerMessagingComponent(DiscussMobileMailboxSelectionView);
