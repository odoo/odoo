/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component, onMounted, onPatched, onWillUnmount, useRef } = owl;

export class ChatWindowHiddenMenu extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        this._onClickCaptureGlobal = this._onClickCaptureGlobal.bind(this);
        /**
         * Reference of the dropup list. Useful to auto-set max height based on
         * browser screen height.
         */
        this._listRef = useRef('list');
        onMounted(() => this._mounted());
        onPatched(() => this._patched());
        onWillUnmount(() => this._willUnmount());
    }

    _mounted() {
        if (!this.root.el) {
            return;
        }
        this._apply();
        document.addEventListener('click', this._onClickCaptureGlobal, true);
    }

    _patched() {
        if (!this.root.el) {
            return;
        }
        this._apply();
    }

    _willUnmount() {
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
        const offset = this.messaging.chatWindowManager.visual.hiddenMenuOffset;
        this.root.el.style[offsetFrom] = `${offset}px`;
        this.root.el.style[oppositeFrom] = 'auto';
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
        if (!this.root.el || this.root.el.contains(ev.target)) {
            return;
        }
        this.messaging.chatWindowManager.closeHiddenMenu();
    }

}

Object.assign(ChatWindowHiddenMenu, {
    props: {},
    template: 'mail.ChatWindowHiddenMenu',
});

registerMessagingComponent(ChatWindowHiddenMenu);
