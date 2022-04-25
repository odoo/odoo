/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class NotificationList extends Component {

    /**
     * @returns {NotificationListView}
     */
    get notificationListView() {
        return this.messaging && this.messaging.models['NotificationListView'].get(this.props.localId);
    }

}

Object.assign(NotificationList, {
    props: { localId: String },
    template: 'mail.NotificationList',
});

registerMessagingComponent(NotificationList);
