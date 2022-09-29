/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChatWindowHeader extends Component {

    /**
     * @returns {ChatWindowHeaderView}
     */
     get chatWindowHeaderView() {
        return this.props.record;
    }

}

Object.assign(ChatWindowHeader, {
    props: { record: Object },
    template: 'mail.ChatWindowHeader',
});

registerMessagingComponent(ChatWindowHeader);
