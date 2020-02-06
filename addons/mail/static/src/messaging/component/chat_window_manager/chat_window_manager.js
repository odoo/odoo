odoo.define('mail.messaging.component.ChatWindowManager', function (require) {
'use strict';

const components = {
    ChatWindow: require('mail.messaging.component.ChatWindow'),
    ChatWindowHiddenMenu: require('mail.messaging.component.ChatWindowHiddenMenu'),
};
const useStore = require('mail.messaging.component_hook.useStore');

const { Component } = owl;

class ChatWindowManager extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            return {
                chatWindowVisual: this.env.entities.ChatWindow.visual,
                device: this.env.messaging.device,
            };
        });
    }

}

Object.assign(ChatWindowManager, {
    components,
    props: {},
    template: 'mail.messaging.component.ChatWindowManager',
});

return ChatWindowManager;

});
