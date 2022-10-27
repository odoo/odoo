/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

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
