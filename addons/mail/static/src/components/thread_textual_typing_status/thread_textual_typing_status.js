/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ThreadTextualTypingStatus extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.thread}
     */
    get thread() {
        return this.messaging && this.messaging.models['mail.thread'].get(this.props.threadLocalId);
    }

}

Object.assign(ThreadTextualTypingStatus, {
    props: {
        threadLocalId: String,
    },
    template: 'mail.ThreadTextualTypingStatus',
});

registerMessagingComponent(ThreadTextualTypingStatus);
