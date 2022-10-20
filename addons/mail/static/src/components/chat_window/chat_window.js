/** @odoo-module **/

import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChatWindow extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useUpdateToModel({ methodName: 'onComponentUpdate' });
    }

    /**
     * @returns {ChatWindow}
     */
    get chatWindow() {
        return this.props.record;
    }

}

Object.assign(ChatWindow, {
    props: { record: Object },
    template: 'mail.ChatWindow',
});

registerMessagingComponent(ChatWindow);
