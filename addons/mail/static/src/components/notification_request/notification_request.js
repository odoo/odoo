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

}

Object.assign(NotificationRequest, {
    props: { localId: String },
    template: 'mail.NotificationRequest',
});

registerMessagingComponent(NotificationRequest);
