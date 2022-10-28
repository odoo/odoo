/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class NotificationRequestView extends Component {

    /**
     * @returns {NotificationRequestView}
     */
    get notificationRequestView() {
        return this.props.record;
    }

}

Object.assign(NotificationRequestView, {
    props: { record: Object },
    template: 'mail.NotificationRequestView',
});

registerMessagingComponent(NotificationRequestView);
