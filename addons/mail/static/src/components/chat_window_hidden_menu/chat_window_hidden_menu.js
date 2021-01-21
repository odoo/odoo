odoo.define('mail/static/src/components/chat_window_hidden_menu/chat_window_hidden_menu.js', function (require) {
'use strict';

const components = {
    ChatWindowHeader: require('mail/static/src/components/chat_window_header/chat_window_header.js'),
};
const useShouldUpdateBasedOnProps = require('mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;
const { useRef } = owl.hooks;

class ChatWindowHiddenMenu extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const chatWindowManager = this.env.messaging.chatWindowManager;
            const device = this.env.messaging.device;
            const locale = this.env.messaging.locale;
            return {
                chatWindowManager: chatWindowManager ? chatWindowManager.__state : undefined,
                device: device ? device.__state : undefined,
                localeTextDirection: locale ? locale.textDirection : undefined,
            };
        });
        this._onClickCaptureGlobal = this._onClickCaptureGlobal.bind(this);
        /**
         * Reference of the dropup list. Useful to auto-set max height based on
         * browser screen height.
         */
        this._listRef = useRef('list');
        /**
         * The intent of the toggle button depends on the last rendered state.
         */
        this._wasMenuOpen;
    }

    mounted() {
        this._apply();
        document.addEventListener('click', this._onClickCaptureGlobal, true);
    }

    patched() {
        this._apply();
    }

    willUnmount() {
        document.removeEventListener('click', this._onClickCaptureGlobal, true);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _apply() {
        this._applyListHeight();
        this._applyOffset();
        this._wasMenuOpen = this.env.messaging.chatWindowManager.isHiddenMenuOpen;
    }

    /**
     * @private
     */
    _applyListHeight() {
        const device = this.env.messaging.device;
        const height = device.globalWindowInnerHeight / 2;
        this._listRef.el.style['max-height'] = `${height}px`;
    }

    /**
     * @private
     */
    _applyOffset() {
        const textDirection = this.env.messaging.locale.textDirection;
        const offsetFrom = textDirection === 'rtl' ? 'left' : 'right';
        const oppositeFrom = offsetFrom === 'right' ? 'left' : 'right';
        const offset = this.env.messaging.chatWindowManager.visual.hidden.offset;
        this.el.style[offsetFrom] = `${offset}px`;
        this.el.style[oppositeFrom] = 'auto';
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Closes the menu when clicking outside.
     * Must be done as capture to avoid stop propagation.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickCaptureGlobal(ev) {
        if (this.el.contains(ev.target)) {
            return;
        }
        this.env.messaging.chatWindowManager.closeHiddenMenu();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickToggle(ev) {
        if (this._wasMenuOpen) {
            this.env.messaging.chatWindowManager.closeHiddenMenu();
        } else {
            this.env.messaging.chatWindowManager.openHiddenMenu();
        }
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {mail.chat_window} ev.detail.chatWindow
     */
    _onClickedChatWindow(ev) {
        const chatWindow = ev.detail.chatWindow;
        chatWindow.makeActive();
        this.env.messaging.chatWindowManager.closeHiddenMenu();
    }

}

Object.assign(ChatWindowHiddenMenu, {
    components,
    props: {},
    template: 'mail.ChatWindowHiddenMenu',
});

return ChatWindowHiddenMenu;

});
