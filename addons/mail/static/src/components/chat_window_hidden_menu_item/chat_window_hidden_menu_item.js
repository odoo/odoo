/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChatWindowHiddenMenuItem extends Component {

    /**
     * @returns {ChatWindowHeaderView}
     */
     get chatWindowHeaderView() {
        return this.props.chatWindowHeaderView;
    }
}

Object.assign(ChatWindowHiddenMenuItem, {
    defaultProps: {
        isLast: false,
    },
    props: {
        chatWindowHeaderView: Object,
        isLast: {
            type: Boolean,
            optional: true,
        },
    },
    template: 'mail.ChatWindowHiddenMenuItem',
});

registerMessagingComponent(ChatWindowHiddenMenuItem);
