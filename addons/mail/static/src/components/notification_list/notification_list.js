/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class NotificationList extends Component {

    /**
     * @returns {NotificationListView}
     */
    get notificationListView() {
        return this.props.record;
    }

}

Object.assign(NotificationList, {
    props: { record: Object },
    template: 'mail.NotificationList',
});

registerMessagingComponent(NotificationList);
