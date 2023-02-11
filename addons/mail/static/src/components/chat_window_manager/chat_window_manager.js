/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChatWindowManager extends Component {}

Object.assign(ChatWindowManager, {
    props: {},
    template: 'mail.ChatWindowManager',
});

registerMessagingComponent(ChatWindowManager);
