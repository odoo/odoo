/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class NotificationAlert extends Component {}
Object.assign(NotificationAlert, {
    template: 'mail.NotificationAlert',
});
registerMessagingComponent(NotificationAlert);
