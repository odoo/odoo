/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ThreadTextualTypingStatus extends Component {

    /**
     * @returns {Thread}
     */
    get thread() {
        return this.props.thread;
    }

}

Object.assign(ThreadTextualTypingStatus, {
    props: { thread: Object },
    template: 'mail.ThreadTextualTypingStatus',
});

registerMessagingComponent(ThreadTextualTypingStatus);
