/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class NotificationListView extends Component {

    /**
     * @returns {NotificationListView}
     */
    get notificationListView() {
        return this.props.record;
    }

}

Object.assign(NotificationListView, {
    props: { record: Object },
    template: 'mail.NotificationListView',
});

registerMessagingComponent(NotificationListView);
