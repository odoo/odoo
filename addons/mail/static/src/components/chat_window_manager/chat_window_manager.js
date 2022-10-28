/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class ChatWindowManager extends Component {}

Object.assign(ChatWindowManager, {
    props: { record: Object },
    template: 'mail.ChatWindowManager',
});

registerMessagingComponent(ChatWindowManager);
