/** @odoo-module **/

import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import useStore from '@mail/component_hooks/use_store/use_store';
import ChatWindow from '@mail/components/chat_window/chat_window';
import ChatWindowHiddenMenu from '@mail/components/chat_window_hidden_menu/chat_window_hidden_menu';

const { Component } = owl;

const components = { ChatWindow, ChatWindowHiddenMenu };

class ChatWindowManager extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const chatWindowManager = this.env.messaging && this.env.messaging.chatWindowManager;
            const allOrderedVisible = chatWindowManager
                ? chatWindowManager.allOrderedVisible
                : [];
            return {
                allOrderedVisible,
                allOrderedVisibleThread: allOrderedVisible.map(chatWindow => chatWindow.thread),
                chatWindowManager,
                chatWindowManagerHasHiddenChatWindows: chatWindowManager && chatWindowManager.hasHiddenChatWindows,
                isMessagingInitialized: this.env.isMessagingInitialized(),
            };
        }, {
            compareDepth: {
                allOrderedVisible: 1,
                allOrderedVisibleThread: 1,
            },
        });
    }

}

Object.assign(ChatWindowManager, {
    components,
    props: {},
    template: 'mail.ChatWindowManager',
});

export default ChatWindowManager;
