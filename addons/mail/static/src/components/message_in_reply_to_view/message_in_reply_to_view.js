/** @odoo-module */

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class MessageInReplyToView extends Component {

    /**
     * @returns {MessageInReplyToView}
     */
    get messageInReplyToView() {
        return this.props.record;
    }
}

Object.assign(MessageInReplyToView, {
    props: { record: Object },
    template: "mail.MessageInReplyToView",
});

registerMessagingComponent(MessageInReplyToView);
