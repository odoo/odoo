/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class MessageReactionGroup extends Component {

    get messageReactionGroup() {
        return this.props.record;
    }

}

Object.assign(MessageReactionGroup, {
    props: { record: Object },
    template: 'mail.MessageReactionGroup',
});

registerMessagingComponent(MessageReactionGroup);
