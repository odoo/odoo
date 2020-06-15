odoo.define('mail/static/src/components/chat_window_manager/chat_window_manager.js', function (require) {
'use strict';

const components = {
    ChatWindow: require('mail/static/src/components/chat_window/chat_window.js'),
    ChatWindowHiddenMenu: require('mail/static/src/components/chat_window_hidden_menu/chat_window_hidden_menu.js'),
};
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;

class ChatWindowManager extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            return {
                chatWindowManagerVisual: this.env.messaging.chatWindowManager.visual,
                device: this.env.messaging.device,
            };
        });
    }

}

Object.assign(ChatWindowManager, {
    components,
    props: {},
    template: 'mail.ChatWindowManager',
});

return ChatWindowManager;

});
