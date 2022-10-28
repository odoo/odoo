/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

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
