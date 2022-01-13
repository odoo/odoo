/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DiscussSidebarMailbox extends Component {

    /**
     * @returns {Thread}
     */
    get mailbox() {
        return this.messaging.models['Thread'].get(this.props.threadLocalId);
    }

}

Object.assign(DiscussSidebarMailbox, {
    props: { threadLocalId: String },
    template: 'mail.DiscussSidebarMailbox',
});

registerMessagingComponent(DiscussSidebarMailbox);
