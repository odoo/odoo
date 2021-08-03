/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models/use_models';
import { useShouldUpdateBasedOnProps } from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import { ChatWindow } from '@mail/components/chat_window/chat_window';
import { ChatWindowHiddenMenu } from '@mail/components/chat_window_hidden_menu/chat_window_hidden_menu';

const { Component } = owl;

const components = { ChatWindow, ChatWindowHiddenMenu };

export class ChatWindowManager extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useModels();
    }

}

Object.assign(ChatWindowManager, {
    components,
    props: {},
    template: 'mail.ChatWindowManager',
});
