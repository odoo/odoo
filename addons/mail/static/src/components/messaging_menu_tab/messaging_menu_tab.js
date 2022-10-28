/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessagingMenuTabView extends Component {

    /**
     * @returns {MessagingMenuTabView}
     */
    get messagingMenuTabView() {
        return this.props.record;
    }

}

Object.assign(MessagingMenuTabView, {
    props: { record: Object },
    template: 'mail.MessagingMenuTabView',
});

registerMessagingComponent(MessagingMenuTabView);
