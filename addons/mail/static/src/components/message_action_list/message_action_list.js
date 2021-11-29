/** @odoo-module */

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useHtmlRefToModel } from '@mail/component_hooks/use_html_ref_to_model/use_html_ref_to_model';

const { Component } = owl;

export class MessageActionList extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useHtmlRefToModel({ fieldName: 'reactionPopoverRef', modelName: 'mail.message_action_list', propNameAsRecordLocalId: 'messageActionListLocalId', refName: 'reactionPopover' });
        this.ADD_A_REACTION = this.env._t("Add a Reaction");
    }

    /**
     * @returns {mail.message}
     */
    get messageActionList() {
        return this.messaging && this.messaging.models['mail.message_action_list'].get(this.props.messageActionListLocalId);
    }

}

Object.assign(MessageActionList, {
    props: {
        messageActionListLocalId: String,
    },
    template: "mail.MessageActionList",
});

registerMessagingComponent(MessageActionList);
