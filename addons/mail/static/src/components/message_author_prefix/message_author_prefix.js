/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageAuthorPrefix extends Component {

    /**
     * @returns {messageAuthorPrefixView}
     */
    get messageAuthorPrefixView() {
        return this.messaging && this.messaging.models['MessageAuthorPrefixView'].get(this.props.localId);
    }

    /**
     * @returns {Message}
     */
    get message() {
        return this.messaging && this.messaging.models['Message'].get(this.props.messageLocalId);
    }

    /**
     * @returns {Thread|undefined}
     */
    get thread() {
        return this.messaging && this.messaging.models['Thread'].get(this.props.threadLocalId);
    }

}

Object.assign(MessageAuthorPrefix, {
    props: {
        localId: String,
        messageLocalId: String,
        threadLocalId: {
            type: String,
            optional: true,
        },
    },
    template: 'mail.MessageAuthorPrefix',
});

registerMessagingComponent(MessageAuthorPrefix);
