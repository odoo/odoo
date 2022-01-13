/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ThreadIcon extends Component {

    /**
     * @returns {Thread}
     */
    get thread() {
        return this.messaging && this.messaging.models['Thread'].get(this.props.threadLocalId);
    }

}

Object.assign(ThreadIcon, {
    props: { threadLocalId: String },
    template: 'mail.ThreadIcon',
});

registerMessagingComponent(ThreadIcon);
