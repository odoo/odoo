/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageReactionGroupView extends Component {

    get messageReactionGroupView() {
        return this.props.record;
    }

}

Object.assign(MessageReactionGroupView, {
    props: { record: Object },
    template: 'mail.MessageReactionGroupView',
});

registerMessagingComponent(MessageReactionGroupView);
