/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageReactionGroupItem extends Component {

    /**
     * @returns {MessageReactionGroupItem}
     */
    get messageReactionGroupItem() {
        return this.props.record;
    }

}

Object.assign(MessageReactionGroupItem, {
    props: { record: Object },
    template: 'mail.MessageReactionGroupItem',
});

registerMessagingComponent(MessageReactionGroupItem);
