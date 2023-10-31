/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ThreadIcon extends Component {

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

Object.assign(ThreadIcon, {
    props: {
        threadLocalId: String,
    },
    template: 'mail.ThreadIcon',
});

registerMessagingComponent(ThreadIcon);
