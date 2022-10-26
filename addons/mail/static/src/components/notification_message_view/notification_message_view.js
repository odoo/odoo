/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

class NotificationMessageView extends Component {

    /**
     * @returns {NotificationMessageView}
     */
    get notificationMessageView() {
        return this.props.record;
    }

}

Object.assign(NotificationMessageView, {
    props: { record: Object },
    template: 'mail.NotificationMessageView',
});

registerMessagingComponent(NotificationMessageView);
