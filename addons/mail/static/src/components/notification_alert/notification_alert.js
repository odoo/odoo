/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class NotificationAlert extends Component {}
Object.assign(NotificationAlert, {
    template: 'mail.NotificationAlert',
});
registerMessagingComponent(NotificationAlert);
