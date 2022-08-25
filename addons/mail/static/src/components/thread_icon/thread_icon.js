/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ThreadIcon extends Component {

    /**
     * @returns {Thread}
     */
    get thread() {
        return this.props.thread;
    }

}

Object.assign(ThreadIcon, {
    props: { thread: Object },
    template: 'mail.ThreadIcon',
});

registerMessagingComponent(ThreadIcon);
