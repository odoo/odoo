/** @odoo-module */

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageInReplyToView extends Component {
    /**
     * @returns {mail.message_in_reply_to_view}
     */
    get messageInReplyToView() {
        return this.messaging && this.messaging.models['mail.message_in_reply_to_view'].get(this.props.messageInReplyToViewLocalId);
    }
}

Object.assign(MessageInReplyToView, {
    props: { messageInReplyToViewLocalId: String },
    template: "mail.MessageInReplyToView",
});

registerMessagingComponent(MessageInReplyToView);
