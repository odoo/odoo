/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessagingMenuTab extends Component {

    /**
     * @returns {MessagingMenuTabView}
     */
    get messagingMenuTabView() {
        return this.props.record;
    }

}

Object.assign(MessagingMenuTab, {
    props: { record: Object },
    template: 'mail.MessagingMenuTab',
});

registerMessagingComponent(MessagingMenuTab);
