/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class Notification extends Component {

    /**
     * @returns {ThreadPreviewView}
     */
    get threadPreviewView() {
        return this.messaging && this.messaging.models['ThreadPreviewView'].get(this.props.localId);
    }

    /**
     * @returns {ThreadNeedactionPreviewView}
     */
    get threadNeedactionPreviewView() {
        return this.messaging && this.messaging.models['ThreadNeedactionPreviewView'].get(this.props.localId);
    }

    /**
     * @returns {NotificationGroupView}
     */
    get notificationGroupView() {
        return this.messaging && this.messaging.models['NotificationGroupView'].get(this.props.localId);
    }

    /**
     * @returns {NotificationRequestView}
     */
    get notificationRequestView() {
        return this.messaging && this.messaging.models['NotificationRequestView'].get(this.props.localId);
    }

}

Object.assign(Notification, {
    defaultProps: {
        isLast: false,
    },
    props: {
        isLast: {
            type: Boolean,
            optional: true,
        },
        localId: String,
    },
    template: 'mail.Notification',
});

registerMessagingComponent(Notification);
