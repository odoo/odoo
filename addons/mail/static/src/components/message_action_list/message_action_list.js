/** @odoo-module */

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';

const { Component } = owl;

export class MessageActionList extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'reactionPopoverRef', modelName: 'MessageActionList', propNameAsRecordLocalId: 'messageActionListLocalId', refName: 'reactionPopover' });
        this.ADD_A_REACTION = this.env._t("Add a Reaction");
    }

    /**
     * @returns {MessageActionList}
     */
    get messageActionList() {
        return this.messaging && this.messaging.models['MessageActionList'].get(this.props.messageActionListLocalId);
    }

}

Object.assign(MessageActionList, {
    props: {
        messageActionListLocalId: String,
    },
    template: "mail.MessageActionList",
});

registerMessagingComponent(MessageActionList);
