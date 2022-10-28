/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

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
