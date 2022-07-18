/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;
const { useRef } = owl.hooks;

export class ChatWindowHiddenMenu extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
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
        if (!this.messaging) {
            return;
        }
        this._applyListHeight();
        this._applyOffset();
        this._wasMenuOpen = this.messaging.chatWindowManager.isHiddenMenuOpen;
    }

    /**
     * @private
     */
    _applyListHeight() {
        const device = this.messaging.device;
        const height = device.globalWindowInnerHeight / 2;
        this._listRef.el.style['max-height'] = `${height}px`;
    }

    /**
     * @private
     */
    _applyOffset() {
        const textDirection = this.messaging.locale.textDirection;
        const offsetFrom = textDirection === 'rtl' ? 'left' : 'right';
        const oppositeFrom = offsetFrom === 'right' ? 'left' : 'right';
        const offset = this.messaging.chatWindowManager.visual.hidden.offset;
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
        if (!this.el || this.el.contains(ev.target)) {
            return;
        }
        this.messaging.chatWindowManager.closeHiddenMenu();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickToggle(ev) {
        if (this._wasMenuOpen) {
            this.messaging.chatWindowManager.closeHiddenMenu();
        } else {
            this.messaging.chatWindowManager.openHiddenMenu();
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
        this.messaging.chatWindowManager.closeHiddenMenu();
    }

}

Object.assign(ChatWindowHiddenMenu, {
    props: {},
    template: 'mail.ChatWindowHiddenMenu',
});

registerMessagingComponent(ChatWindowHiddenMenu);
