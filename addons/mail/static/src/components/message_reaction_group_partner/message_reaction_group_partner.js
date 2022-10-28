/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageReactionGroupPartner extends Component {

    /**
     * @returns {MessageReactionGroupPartner}
     */
    get messageReactionGroupPartner() {
        return this.props.record;
    }

}

Object.assign(MessageReactionGroupPartner, {
    props: { record: Object },
    template: 'mail.MessageReactionGroupPartner',
});

registerMessagingComponent(MessageReactionGroupPartner);
