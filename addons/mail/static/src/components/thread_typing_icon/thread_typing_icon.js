/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ThreadTypingIcon extends Component {

    /**
     * @returns {ThreadTypingIconView}
     */
    get threadTypingIconView() {
        return this.props.record;
    }

}

Object.assign(ThreadTypingIcon, {
    props: { record: Object },
    template: 'mail.ThreadTypingIcon',
});

registerMessagingComponent(ThreadTypingIcon);
