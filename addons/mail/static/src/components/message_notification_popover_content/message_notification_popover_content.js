/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageNotificationPopoverContent extends Component {

    /**
     * @returns {MessageView}
     */
    get messageView() {
        return this.messaging && this.messaging.models['MessageView'].get(this.props.localId);
    }

}

Object.assign(MessageNotificationPopoverContent, {
    props: { localId: String },
    template: 'mail.MessageNotificationPopoverContent',
});

registerMessagingComponent(MessageNotificationPopoverContent);
