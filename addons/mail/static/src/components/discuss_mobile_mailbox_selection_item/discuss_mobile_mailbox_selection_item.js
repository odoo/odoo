/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class DiscussMobileMailboxSelectionItemView extends Component {

    /**
     * @returns {DiscussMobileMailboxSelectionItemView}
     */
    get discussMobileMailboxSelectionItemView() {
        return this.props.record;
    }

}

Object.assign(DiscussMobileMailboxSelectionItemView, {
    props: { record: Object },
    template: 'mail.DiscussMobileMailboxSelectionItemView',
});

registerMessagingComponent(DiscussMobileMailboxSelectionItemView);
