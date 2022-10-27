/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

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
