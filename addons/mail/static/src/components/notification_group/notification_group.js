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
        useRefToModel({ fieldName: 'markAsReadRef', refName: 'markAsRead' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {NotificationGroupView}
     */
    get notificationGroupView() {
        return this.props.record;
    }

}

Object.assign(NotificationGroup, {
    props: { record: Object },
    template: 'mail.NotificationGroup',
});

registerMessagingComponent(NotificationGroup);
