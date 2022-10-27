/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChatWindowHiddenMenuItemView extends Component {

    /**
     * @returns {ChatWindowHiddenMenuItemView}
     */
    get chatWindowHiddenMenuItemView() {
        return this.props.record;
    }

}

Object.assign(ChatWindowHiddenMenuItemView, {
    props: { record: Object },
    template: 'mail.ChatWindowHiddenMenuItemView',
});

registerMessagingComponent(ChatWindowHiddenMenuItemView);
