odoo.define('mail.messaging.component.ChatWindowHiddenMenu', function (require) {
'use strict';

const components = {
    ChatWindowHeader: require('mail.messaging.component.ChatWindowHeader'),
};
const useStore = require('mail.messaging.component_hook.useStore');

const { Component } = owl;
const { useRef } = owl.hooks;

class ChatWindowHiddenMenu extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            return {
                chatWindowVisual: this.env.entities.ChatWindow.visual,
                device: this.env.messaging.device,
                isHiddenMenuOpen: this.env.entities.ChatWindow.isHiddenMenuOpen,
                localeTextDirection: this.env.messaging.locale.textDirection,
            };
        });
        this._onClickCaptureGlobal = this._onClickCaptureGlobal.bind(this);
        /**
         * Reference of the dropup list. Useful to auto-set max height based on
         * browser screen height.
         */
        this._listRef = useRef('list');
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
        const offset = this.env.entities.ChatWindow.visual.hidden.offset;
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
        this.env.entities.ChatWindow.closeHiddenMenu();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickToggle(ev) {
        ev.stopPropagation();
        this.env.entities.ChatWindow.toggleHiddenMenu();
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {mail.messaging.entity.ChatWindow} ev.detail.chatWindow
     */
    _onClickedChatWindow(ev) {
        ev.detail.chatWindow.makeVisible();
        this.env.entities.ChatWindow.closeHiddenMenu();
    }

}

Object.assign(ChatWindowHiddenMenu, {
    components,
    props: {},
    template: 'mail.messaging.component.ChatWindowHiddenMenu',
});

return ChatWindowHiddenMenu;

});
