/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageNotificationPopoverContent extends Component {

    /**
     * @returns {MessageNotificationPopoverContentView}
     */
    get messageNotificationPopoverContentView() {
        return this.props.record;
    }

}

Object.assign(MessageNotificationPopoverContent, {
    props: { record: Object },
    template: 'mail.MessageNotificationPopoverContent',
});

registerMessagingComponent(MessageNotificationPopoverContent);
