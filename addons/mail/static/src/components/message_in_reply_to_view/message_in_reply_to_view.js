/** @odoo-module */

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageInReplyToView extends Component {

    /**
     * @returns {MessageInReplyToView}
     */
    get messageInReplyToView() {
        return this.messaging && this.messaging.models['MessageInReplyToView'].get(this.props.localId);
    }
}

Object.assign(MessageInReplyToView, {
    props: { localId: String },
    template: "mail.MessageInReplyToView",
});

registerMessagingComponent(MessageInReplyToView);
