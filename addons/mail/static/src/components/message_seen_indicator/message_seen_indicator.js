/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageSeenIndicator extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {Message}
     */
    get message() {
        return this.messaging && this.messaging.models['Message'].get(this.props.messageLocalId);
    }

    /**
     * @returns {MessageSeenIndicator}
     */
     get messageSeenIndicatorView() {
        return this.messaging && this.messaging.models['MessageSeenIndicatorView'].get(this.props.localId);
    }
}

Object.assign(MessageSeenIndicator, {
    props: {
        localId: String,
        messageLocalId: String,
    },
    template: 'mail.MessageSeenIndicator',
});

registerMessagingComponent(MessageSeenIndicator);
