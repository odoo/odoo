/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageAuthorPrefix extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.message}
     */
    get message() {
        return this.messaging && this.messaging.models['mail.message'].get(this.props.messageLocalId);
    }

    /**
     * @returns {mail.thread|undefined}
     */
    get thread() {
        return this.messaging && this.messaging.models['mail.thread'].get(this.props.threadLocalId);
    }

}

Object.assign(MessageAuthorPrefix, {
    props: {
        messageLocalId: String,
        threadLocalId: {
            type: String,
            optional: true,
        },
    },
    template: 'mail.MessageAuthorPrefix',
});

registerMessagingComponent(MessageAuthorPrefix);
