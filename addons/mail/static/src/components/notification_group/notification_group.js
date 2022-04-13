/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class NotificationGroup extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'markAsReadRef', modelName: 'NotificationGroupView', refName: 'markAsRead' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {NotificationGroupView}
     */
    get notificationGroupView() {
        return this.messaging && this.messaging.models['NotificationGroupView'].get(this.props.localId);
    }

    /**
     * @returns {string|undefined}
     */
    image() {
        if (this.notificationGroupView.notificationGroup.notification_type === 'email') {
            return '/mail/static/src/img/smiley/mailfailure.jpg';
        }
    }

}

Object.assign(NotificationGroup, {
    props: { localId: String },
    template: 'mail.NotificationGroup',
});

registerMessagingComponent(NotificationGroup);
