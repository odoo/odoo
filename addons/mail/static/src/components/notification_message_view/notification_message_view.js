/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

class NotificationMessageView extends Component {

    /**
     * @override
     */
     setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        useUpdateToModel({ methodName: 'onComponentUpdate' });
    }

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
