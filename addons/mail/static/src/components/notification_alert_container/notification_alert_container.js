/** @odoo-module **/

import { registry } from "@web/core/registry";
import { getMessagingComponent } from "@mail/utils/messaging_component";

const { Component } = owl;

export class NotificationAlertContainer extends Component {}
Object.assign(NotificationAlertContainer, {
    components: { NotificationAlert: getMessagingComponent('NotificationAlert') },
    template: 'mail.NotificationAlertContainer',
});
registry.category("view_widgets").add(
    "notification_alert",
    NotificationAlertContainer
);
