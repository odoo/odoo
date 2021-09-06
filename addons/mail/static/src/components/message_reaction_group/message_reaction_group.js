/** @odoo-module **/

const { Component } = owl;
import { registerMessagingComponent } from '@mail/utils/messaging_component';

export class MessageReactionGroup extends Component {

    get messageReactionGroup() {
        return this.messaging.models['mail.message_reaction_group'].get(this.props.messageReactionGroupLocalId);
    }

}

Object.assign(MessageReactionGroup, {
    props: {
        messageReactionGroupLocalId: String,
    },
    template: 'mail.MessageReactionGroup',
});

registerMessagingComponent(MessageReactionGroup);
