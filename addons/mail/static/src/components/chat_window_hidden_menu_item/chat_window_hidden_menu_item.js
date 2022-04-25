/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChatWindowHiddenMenuItem extends Component {

    /**
     * @returns {ChatWindowHeaderView}
     */
     get chatWindowHeaderView() {
        return this.messaging && this.messaging.models['ChatWindowHeaderView'].get(this.props.chatWindowHeaderViewLocalId);
    }
}

Object.assign(ChatWindowHiddenMenuItem, {
    defaultProps: {
        isLast: false,
    },
    props: {
        chatWindowHeaderViewLocalId: String,
        isLast: {
            type: Boolean,
            optional: true,
        },
    },
    template: 'mail.ChatWindowHiddenMenuItem',
});

registerMessagingComponent(ChatWindowHiddenMenuItem);
