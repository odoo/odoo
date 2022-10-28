/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useModels } from '@mail/component_hooks/use_models';
import { getMessagingComponent } from "@mail/utils/messaging_component";

import { Component } from '@odoo/owl';

export class NotificationAlertContainer extends Component {
    /**
     * @override
     */
    setup() {
        useModels();
        super.setup();
    }

    get messaging() {
        return this.env.services.messaging.modelManager.messaging;
    }
}
Object.assign(NotificationAlertContainer, {
    components: { NotificationAlertView: getMessagingComponent('NotificationAlertView') },
    template: 'mail.NotificationAlertContainer',
    props: {
        // Should call standard_widget_props.js
        readonly: { type: Boolean, optional: true },
        record: { type: Object },
    },
});
registry.category("view_widgets").add(
    "notification_alert",
    NotificationAlertContainer
);
