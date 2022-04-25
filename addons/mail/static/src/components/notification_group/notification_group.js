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

}

Object.assign(NotificationGroup, {
    props: { localId: String },
    template: 'mail.NotificationGroup',
});

registerMessagingComponent(NotificationGroup);
