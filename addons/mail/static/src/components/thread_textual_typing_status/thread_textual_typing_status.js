/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ThreadTextualTypingStatusView extends Component {

    /**
     * @returns {ThreadTextualTypingStatusView}
     */
    get threadTextualTypingStatusView() {
        return this.props.record;
    }

}

Object.assign(ThreadTextualTypingStatusView, {
    props: { record: Object },
    template: 'mail.ThreadTextualTypingStatusView',
});

registerMessagingComponent(ThreadTextualTypingStatusView);
