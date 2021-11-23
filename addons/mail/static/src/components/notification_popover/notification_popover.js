/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class NotificationPopover extends Component {

    /**
     * @returns {mail.message_view}
     */
    get messageView() {
        return this.messaging && this.messaging.models['mail.message_view'].get(this.props.messageViewLocalId);
    }

}

Object.assign(NotificationPopover, {
    props: {
        messageViewLocalId: String,
    },
    template: 'mail.NotificationPopover',
});

registerMessagingComponent(NotificationPopover);
