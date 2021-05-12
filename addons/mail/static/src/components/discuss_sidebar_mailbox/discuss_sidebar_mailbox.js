/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DiscussSidebarMailBox extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.thread}
     */
    get mailbox() {
        return this.messaging.models['mail.thread'].get(this.props.threadLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClick() {
        this.mailbox.open();
    }
}

Object.assign(DiscussSidebarMailBox, {
    props: {
        threadLocalId: String,
    },
    template: 'mail.DiscussSidebarMailBox',
});

registerMessagingComponent(DiscussSidebarMailBox);
