/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageContextReactionSummary extends Component {

    /**
     * @returns {MessageContextReactionSummary}
     */
    get messageContextReactionSummary() {
        return this.props.record;
    }

}

Object.assign(MessageContextReactionSummary, {
    props: { record: Object },
    template: 'mail.MessageContextReactionSummary',
});

registerMessagingComponent(MessageContextReactionSummary);
