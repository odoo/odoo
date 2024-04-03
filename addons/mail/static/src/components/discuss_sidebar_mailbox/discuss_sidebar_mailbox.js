/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DiscussSidebarMailbox extends Component {

    /**
     * @returns {DiscussSidebarMailboxView}
     */
    get discussSidebarMailboxView() {
        return this.props.record;
    }

}

Object.assign(DiscussSidebarMailbox, {
    props: { record: Object },
    template: 'mail.DiscussSidebarMailbox',
});

registerMessagingComponent(DiscussSidebarMailbox);
