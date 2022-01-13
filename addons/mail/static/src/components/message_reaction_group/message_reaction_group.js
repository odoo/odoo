/** @odoo-module **/

const { Component } = owl;
import { registerMessagingComponent } from '@mail/utils/messaging_component';

export class MessageReactionGroup extends Component {

    get messageReactionGroup() {
        return this.messaging.models['MessageReactionGroup'].get(this.props.localId);
    }

}

Object.assign(MessageReactionGroup, {
    props: { localId: String },
    template: 'mail.MessageReactionGroup',
});

registerMessagingComponent(MessageReactionGroup);
