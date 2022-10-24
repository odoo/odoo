/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageContextReactionSummery extends Component {

    /**
     * @returns {MessageContextReactionSummery}
     */
    get messageContextReactionSummery() {
        return this.props.record;
    }

}

Object.assign(MessageContextReactionSummery, {
    props: { record: Object },
    template: 'mail.MessageContextReactionSummery',
});

registerMessagingComponent(MessageContextReactionSummery);
