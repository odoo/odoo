/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class NotificationAlertView extends Component {
    /**
     * @returns {NotificationAlertView}
     */
    get notificationAlert() {
        return this.props.record;
    }
}
Object.assign(NotificationAlertView, {
    props: { record: Object },
    template: 'mail.NotificationAlertView',
});
registerMessagingComponent(NotificationAlertView);
