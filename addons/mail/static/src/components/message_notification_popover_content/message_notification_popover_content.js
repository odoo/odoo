/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageNotificationPopoverContentView extends Component {

    /**
     * @returns {MessageNotificationPopoverContentView}
     */
    get messageNotificationPopoverContentView() {
        return this.props.record;
    }

}

Object.assign(MessageNotificationPopoverContentView, {
    props: { record: Object },
    template: 'mail.MessageNotificationPopoverContentView',
});

registerMessagingComponent(MessageNotificationPopoverContentView);
