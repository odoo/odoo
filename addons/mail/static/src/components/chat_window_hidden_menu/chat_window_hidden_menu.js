odoo.define('mail/static/src/components/chat_window_hidden_menu/chat_window_hidden_menu.js', function (require) {
'use strict';

const components = {
    ChatWindowHeader: require('mail/static/src/components/chat_window_header/chat_window_header.js'),
};
const useModels = require('mail/static/src/component_hooks/use_models/use_models.js');

const { Component } = owl;
const { useRef } = owl.hooks;

class ChatWindowHiddenMenu extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useModels();
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
        this._wasMenuOpen = this.env.messaging.__mfield_chatWindowManager(this).__mfield_isHiddenMenuOpen(this);
    }

    /**
     * @private
     */
    _applyListHeight() {
        const device = this.env.messaging.__mfield_device(this);
        const height = device.__mfield_globalWindowInnerHeight(this) / 2;
        this._listRef.el.style['max-height'] = `${height}px`;
    }

    /**
     * @private
     */
    _applyOffset() {
        const textDirection = this.env.messaging.__mfield_locale(this).__mfield_textDirection(this);
        const offsetFrom = textDirection === 'rtl' ? 'left' : 'right';
        const oppositeFrom = offsetFrom === 'right' ? 'left' : 'right';
        const offset = this.env.messaging.__mfield_chatWindowManager(this).__mfield_visual(this).hidden.offset;
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
        this.env.messaging.__mfield_chatWindowManager(this).closeHiddenMenu();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickToggle(ev) {
        if (this._wasMenuOpen) {
            this.env.messaging.__mfield_chatWindowManager(this).closeHiddenMenu();
        } else {
            this.env.messaging.__mfield_chatWindowManager(this).openHiddenMenu();
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
        this.env.messaging.__mfield_chatWindowManager(this).closeHiddenMenu();
    }

}

Object.assign(ChatWindowHiddenMenu, {
    components,
    props: {},
    template: 'mail.ChatWindowHiddenMenu',
});

return ChatWindowHiddenMenu;

});
