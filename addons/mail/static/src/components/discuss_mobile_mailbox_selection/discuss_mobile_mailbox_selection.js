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
        return this.props.record;
    }

}

Object.assign(DiscussMobileMailboxSelection, {
    props: { record: Object },
    template: 'mail.DiscussMobileMailboxSelection',
});

registerMessagingComponent(DiscussMobileMailboxSelection);
