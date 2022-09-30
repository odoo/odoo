/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ThreadTextualTypingStatus extends Component {

    /**
     * @returns {ThreadTextualTypingStatusView}
     */
    get threadTextualTypingStatusView() {
        return this.props.record;
    }

}

Object.assign(ThreadTextualTypingStatus, {
    props: { record: Object },
    template: 'mail.ThreadTextualTypingStatus',
});

registerMessagingComponent(ThreadTextualTypingStatus);
