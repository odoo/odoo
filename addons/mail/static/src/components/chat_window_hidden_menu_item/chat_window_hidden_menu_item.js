/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChatWindowHiddenMenuItem extends Component {

    /**
     * @returns {ChatWindowHiddenMenuItemView}
     */
    get chatWindowHiddenMenuItemView() {
        return this.props.record;
    }

}

Object.assign(ChatWindowHiddenMenuItem, {
    defaultProps: {
        isLast: false,
    },
    props: {
        isLast: {
            type: Boolean,
            optional: true,
        },
        record: Object,
    },
    template: 'mail.ChatWindowHiddenMenuItem',
});

registerMessagingComponent(ChatWindowHiddenMenuItem);
