/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DiscussSidebarMailbox extends Component {

    /**
     * @returns {DiscussSidebarMailboxView}
     */
    get discussSidebarMailboxView() {
        return this.messaging && this.messaging.models['DiscussSidebarMailboxView'].get(this.props.localId);
    }

}

Object.assign(DiscussSidebarMailbox, {
    props: { localId: String },
    template: 'mail.DiscussSidebarMailbox',
});

registerMessagingComponent(DiscussSidebarMailbox);
