/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class NotificationRequest extends Component {

    /**
     * @returns {NotificationRequestView}
     */
    get notificationRequestView() {
        return this.props.record;
    }

}

Object.assign(NotificationRequest, {
    props: { record: Object },
    template: 'mail.NotificationRequest',
});

registerMessagingComponent(NotificationRequest);
