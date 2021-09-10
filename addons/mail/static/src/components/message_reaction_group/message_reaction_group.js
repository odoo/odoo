/** @odoo-module **/

const { Component } = owl;
import { registerMessagingComponent } from '@mail/utils/messaging_component';

export class MessageReactionGroup extends Component {

    get messageReactionGroupView() {
        return this.messaging.models['mail.message_reaction_group_view'].get(this.props.messageReactionGroupViewLocalId);
    }

}

Object.assign(MessageReactionGroup, {
    props: {
        messageReactionGroupViewLocalId: String,
    },
    template: 'mail.MessageReactionGroup',
});

registerMessagingComponent(MessageReactionGroup);
