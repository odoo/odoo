/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class NotificationGroupView extends Component {

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

Object.assign(NotificationGroupView, {
    props: { record: Object },
    template: 'mail.NotificationGroupView',
});

registerMessagingComponent(NotificationGroupView);
