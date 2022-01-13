/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class NotificationPopover extends Component {

    /**
     * @returns {MessageView}
     */
    get messageView() {
        return this.messaging && this.messaging.models['MessageView'].get(this.props.messageViewLocalId);
    }

}

Object.assign(NotificationPopover, {
    props: { messageViewLocalId: String },
    template: 'mail.NotificationPopover',
});

registerMessagingComponent(NotificationPopover);
