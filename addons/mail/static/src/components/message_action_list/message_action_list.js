/** @odoo-module */

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageActionList extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'actionReactionRef', refName: 'actionReaction' });
    }

    /**
     * @returns {MessageActionList}
     */
    get messageActionList() {
        return this.props.record;
    }

}

Object.assign(MessageActionList, {
    props: { record: Object },
    template: "mail.MessageActionList",
});

registerMessagingComponent(MessageActionList);
