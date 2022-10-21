/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageContextMostUsedImojiView extends Component {
    /**
     * @returns {MessageContextMostUsedImojiView}
     */
    get messageContextMostUsedImojiView() {
        return this.props.record;
    }
}

Object.assign(MessageContextMostUsedImojiView, {
    props: { record: Object },
    template: 'mail.MessageContextMostUsedImojiView',
});

registerMessagingComponent(MessageContextMostUsedImojiView);
