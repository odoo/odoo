/** @odoo-module **/

import { getMessagingComponent, registerMessagingComponent } from '@mail/utils/messaging_component';

import { registry } from '@web/core/registry';

const { Component } = owl;

export class ChatWindowManager extends Component {}

Object.assign(ChatWindowManager, {
    props: {},
    template: 'mail.ChatWindowManager',
});

registerMessagingComponent(ChatWindowManager);

registry.category('main_components').add('mail.chat_window_manager', {
    Component: getMessagingComponent('ChatWindowManager'),
    props: {},
});
