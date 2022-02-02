/** @odoo-module */

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component, markup } = owl;

export class MessageInReplyToView extends Component {

    // Maybe this markup thing could be done earlier ? Like in computePrettyBody. 
    get contentAsMarkup() {
        return markup(this.messageInReplyToView.messageView.message.parentMessage.prettyBody);
    }

    /**
     * @returns {MessageInReplyToView}
     */
    get messageInReplyToView() {
        return this.messaging && this.messaging.models['MessageInReplyToView'].get(this.props.messageInReplyToViewLocalId);
    }
}

Object.assign(MessageInReplyToView, {
    props: { messageInReplyToViewLocalId: String },
    template: "mail.MessageInReplyToView",
});

registerMessagingComponent(MessageInReplyToView);
