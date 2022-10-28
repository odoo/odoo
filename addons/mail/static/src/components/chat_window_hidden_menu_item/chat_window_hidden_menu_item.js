/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class ChatWindowHiddenMenuItem extends Component {

    /**
     * @returns {ChatWindowHiddenMenuItemView}
     */
    get chatWindowHiddenMenuItemView() {
        return this.props.record;
    }

}

Object.assign(ChatWindowHiddenMenuItem, {
    props: { record: Object },
    template: 'mail.ChatWindowHiddenMenuItem',
});

registerMessagingComponent(ChatWindowHiddenMenuItem);
