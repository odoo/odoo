odoo.define('mail/static/src/components/chat_window_header/chat_window_header.js', function (require) {
'use strict';

const components = {
    ThreadIcon: require('mail/static/src/components/thread_icon/thread_icon.js'),
};
const useShouldUpdateBasedOnProps = require('mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;

class ChatWindowHeader extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const chatWindow = this.env.models['mail.chat_window'].get(props.chatWindowLocalId);
            const thread = chatWindow && chatWindow.thread;
            return {
                chatWindow,
                chatWindowHasShiftLeft: chatWindow && chatWindow.hasShiftLeft,
                chatWindowHasShiftRight: chatWindow && chatWindow.hasShiftRight,
                chatWindowName: chatWindow && chatWindow.name,
                isDeviceMobile: this.env.messaging.device.isMobile,
                thread,
                threadLocalMessageUnreadCounter: thread && thread.localMessageUnreadCounter,
                threadMassMailing: thread && thread.mass_mailing,
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.chat_window}
     */
    get chatWindow() {
        return this.env.models['mail.chat_window'].get(this.props.chatWindowLocalId);
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
        if (!this.chatWindow) {
            return;
        }
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
    template: 'mail.ChatWindowHeader',
});

return ChatWindowHeader;

});
