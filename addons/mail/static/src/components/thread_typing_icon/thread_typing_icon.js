/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ThreadTypingIconView extends Component {

    /**
     * @returns {ThreadTypingIconView}
     */
    get threadTypingIconView() {
        return this.props.record;
    }

}

Object.assign(ThreadTypingIconView, {
    props: { record: Object },
    template: 'mail.ThreadTypingIconView',
});

registerMessagingComponent(ThreadTypingIconView);
