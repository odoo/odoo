odoo.define('mail.messaging.component.ChatWindowHeader', function (require) {
'use strict';

const components = {
    ThreadIcon: require('mail.messaging.component.ThreadIcon'),
};
const useStore = require('mail.messaging.component_hook.useStore');

const { Component } = owl;

class ChatWindowHeader extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const chatWindow = this.env.entities.ChatWindow.get(props.chatWindowLocalId);
            return {
                chatWindow,
                chatWindowName: chatWindow && chatWindow.name,
                isDeviceMobile: this.env.messaging.device.isMobile,
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.messaging.entity.ChatWindow}
     */
    get chatWindow() {
        return this.env.entities.ChatWindow.get(this.props.chatWindowLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        const chatWindow = this.chatWindow;
        this.trigger('o-clicked', { chatWindow });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickClose(ev) {
        ev.stopPropagation();
        this.chatWindow.close();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickExpand(ev) {
        ev.stopPropagation();
        this.chatWindow.expand();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickShiftLeft(ev) {
        ev.stopPropagation();
        this.chatWindow.shiftLeft();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickShiftRight(ev) {
        ev.stopPropagation();
        this.chatWindow.shiftRight();
    }

}

Object.assign(ChatWindowHeader, {
    components,
    defaultProps: {
        hasCloseAsBackButton: false,
        isExpandable: false,
    },
    props: {
        chatWindowLocalId: String,
        hasCloseAsBackButton: Boolean,
        isExpandable: Boolean,
    },
    template: 'mail.messaging.component.ChatWindowHeader',
});

return ChatWindowHeader;

});
