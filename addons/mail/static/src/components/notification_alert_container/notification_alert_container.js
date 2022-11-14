/** @odoo-module **/

import { registry } from "@web/core/registry";
import { getMessagingComponent } from "@mail/utils/messaging_component";

import { Component } from "@odoo/owl";

export class NotificationAlertContainer extends Component {}
Object.assign(NotificationAlertContainer, {
    components: { NotificationAlert: getMessagingComponent("NotificationAlert") },
    template: "mail.NotificationAlertContainer",
    props: {
        // Should call standard_widget_props.js
        readonly: { type: Boolean, optional: true },
        record: { type: Object },
    },
});
registry.category("view_widgets").add("notification_alert", NotificationAlertContainer);
