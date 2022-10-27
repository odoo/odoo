/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageView extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        useRefToModel({ fieldName: 'contentRef', refName: 'content' });
        useRefToModel({ fieldName: 'notificationIconRef', refName: 'notificationIcon' });
        useRefToModel({ fieldName: 'prettyBodyRef', refName: 'prettyBody' });
        useUpdateToModel({ methodName: 'onComponentUpdate' });
    }

    /**
     * @returns {MessageView}
     */
    get messageView() {
        return this.props.record;
    }

}

Object.assign(MessageView, {
    props: { record: Object },
    template: 'mail.MessageView',
});

registerMessagingComponent(MessageView);
