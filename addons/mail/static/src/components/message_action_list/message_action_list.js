/** @odoo-module */

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';

const { Component } = owl;

export class MessageActionList extends Component {

    setup() {
        super.setup();
        useRefToModel({ fieldName: 'reactionPopoverRef', modelName: 'mail.message_action_list', propNameAsRecordLocalId: 'actionListLocalId', refName: 'reactionPopover' });
        this.ADD_A_REACTION = this.env._t("Add a Reaction");
    }

    /**
     * @returns {mail.message}
     */
    get actionList() {
        return this.messaging && this.messaging.models['mail.message_action_list'].get(this.props.actionListLocalId);
    }

}

Object.assign(MessageActionList, {
    props: {
        actionListLocalId: String,
        hasMarkAsReadIcon: Boolean,
        hasReplyIcon: Boolean,
    },
    template: "mail.MessageActionList",
});

registerMessagingComponent(MessageActionList);
