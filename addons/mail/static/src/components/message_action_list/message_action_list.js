/** @odoo-module */
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageActionList extends Component {

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
