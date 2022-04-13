/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class NotificationRequest extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {string}
     */
    getHeaderText() {
        return _.str.sprintf(
            this.env._t("%s has a request"),
            this.messaging.partnerRoot.nameOrDisplayName
        );
    }

    /**
     * @returns {NotificationRequestView}
     */
    get notificationRequestView() {
        return this.messaging && this.messaging.models['NotificationRequestView'].get(this.props.localId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClick() {
        if (!this.notificationRequestView) {
            return;
        }
        const windowNotification = this.messaging.browser.Notification;
        const def = windowNotification && windowNotification.requestPermission();
        if (def) {
            def.then(this.notificationRequestView.handleResponseNotificationPermission.bind(this));
        }
        if (!this.messaging.device.isMobile) {
            this.messaging.messagingMenu.close();
        }
    }

}

Object.assign(NotificationRequest, {
    props: { localId: String },
    template: 'mail.NotificationRequest',
});

registerMessagingComponent(NotificationRequest);
