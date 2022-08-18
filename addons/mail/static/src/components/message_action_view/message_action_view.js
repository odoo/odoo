/** @odoo-module */

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageActionView extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'actionRef', refName: 'action' });
    }

    /**
     * @returns {MessageActionView}
     */
    get messageActionView() {
        return this.props.record;
    }

}

Object.assign(MessageActionView, {
    props: { record: Object },
    template: "mail.MessageActionView",
});

registerMessagingComponent(MessageActionView);
