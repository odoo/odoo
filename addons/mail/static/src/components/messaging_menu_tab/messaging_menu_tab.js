/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessagingMenuTab extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {MessagingMenu}
     */
    get messagingMenu() {
        return this.messaging && this.messaging.models['MessagingMenu'].get(this.props.messagingMenuLocalId);
    }

}

Object.assign(MessagingMenuTab, {
    props: {
        messagingMenuLocalId: String,
        tabId: String,
    },
    template: 'mail.MessagingMenuTab',
});

registerMessagingComponent(MessagingMenuTab);
