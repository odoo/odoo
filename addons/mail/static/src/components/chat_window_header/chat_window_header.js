/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChatWindowHeaderView extends Component {

    /**
     * @returns {ChatWindowHeaderView}
     */
     get chatWindowHeaderView() {
        return this.props.record;
    }

}

Object.assign(ChatWindowHeaderView, {
    props: { record: Object },
    template: 'mail.ChatWindowHeaderView',
});

registerMessagingComponent(ChatWindowHeaderView);
