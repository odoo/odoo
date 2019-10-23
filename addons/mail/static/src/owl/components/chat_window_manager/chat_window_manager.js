odoo.define('mail.component.ChatWindowManager', function (require) {
'use strict';

const ChatWindow = require('mail.component.ChatWindow');
const HiddenMenu = require('mail.component.ChatWindowHiddenMenu');

const { Component } = owl;
const { useDispatch, useStore } = owl.hooks;

class ChatWindowManager extends Component {

    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.IS_DEV = true;
        this.TEXT_DIRECTION = this.env._t.database.parameters.direction;
        this.storeDispatch = useDispatch();
        this.storeProps = useStore(state => {
            const {
                autofocusCounter,
                autofocusChatWindowLocalId,
                chatWindowInitialScrollTops,
                computed,
            } = state.chatWindowManager;
            return {
                autofocusCounter,
                autofocusChatWindowLocalId,
                chatWindowInitialScrollTops,
                computed,
                isMobile: state.isMobile,
            };
        });
        /**
         * Attributes that are used to track last autofocused chat window.
         * This is useful to determine if we must autofocus a chat window on
         * store changes. Tracking only last autofocused chat window is not
         * enough in some cases:
         *   - opening a new chat window from messaging menu opens chat window
         *     and auto-focuses it, but this should only occur once
         *   - opening an existing chat window from messaging menu should
         *     auto-focus this chat window, even if it was the last autofocused
         *     chat window and the user focused it out.
         */
        this._lastAutofocusedCounter = 0;
        this._lastAutofocusedChatWindowLocalId = undefined;
        if (this.IS_DEV) {
            window.chat_window_manager = this;
        }
    }

    mounted() {
        this._handleAutofocus();
    }

    patched() {
        this._handleAutofocus();
    }

    //--------------------------------------------------------------------------
    // Getter / Setter
    //--------------------------------------------------------------------------

    /**
     * Determine the direction of chat windows positions.
     *
     * @return {string} either 'rtl' or 'ltr'
     */
    get direction() {
        if (this.TEXT_DIRECTION === 'rtl') {
            return 'ltr';
        } else {
            return 'rtl';
        }
    }

    /**
     * Return list of chat ids ordered by DOM position,
     * i.e. from left to right with this.TEXT_DIRECTION = 'rtl'.
     *
     * @return {Array}
     */
    get orderedVisible() {
        return [...this.storeProps.computed.visible].reverse();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Determine whether the chat window at given index should have shift right
     * command. Right-most chat window should not have this command.
     *
     * @param {integer} index
     * @return {boolean}
     */
    chatWindowShiftRight(index) {
        return index < this.storeProps.computed.visible.length - 1;
    }

    /**
     * Save the scroll positions of chat windows in the store. This happens
     * when chat window manager has to be re-mounted, but the scroll positions
     * should be recovered.
     */
    saveChatWindowsScrollTops() {
        const chatWindowsWithThreadRefs = Object.entries(this.__owl__.refs)
            .filter(([refId, ref]) => refId.startsWith('chatWindow_'))
            .map(([refId, ref]) => ref);
        for (const chatWindowRef of chatWindowsWithThreadRefs) {
            chatWindowRef.saveScrollTop();
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Get references of all chat windows. Useful to set auto-focus when
     * necessary.
     *
     * @private
     * @return {mail.component.ChatWindow}
     */
    _getChatWindowRef(chatWindowLocalId) {
        return this.__owl__.refs[`chatWindow_${chatWindowLocalId}`];
    }

    /**
     * Handle auto-focus of chat windows based on most recent store operation.
     * For instance, when opening a new chat window, it should auto-focus it
     * on mount. There are other scenarios like auto-focusing an existing chat
     * window, which is why auto-focus is dependent of the process flow. We
     * should trust the store with autofocus properties.
     *
     * @private
     */
    _handleAutofocus() {
        let handled = false;
        const dcwm = this.env.store.state.chatWindowManager;
        const lastNotifiedAutofocusCounter = dcwm.notifiedAutofocusCounter;
        if (this.storeProps.isMobile) {
            handled = true; // never autofocus in mobile
        }
        if (
            !handled &&
            this.storeProps.autofocusCounter === lastNotifiedAutofocusCounter
        ) {
            handled = true;
        }
        if (
            !handled &&
            this._lastAutofocusedChatWindowLocalId === this.storeProps.autofocusChatWindowLocalId &&
            this._lastAutofocusedCounter === this.storeProps.autofocusCounter
        ) {
            handled = true;
        }
        if (
            !handled &&
            this._lastAutofocusedChatWindowLocalId === undefined
        ) {
            this._getChatWindowRef(this.storeProps.autofocusChatWindowLocalId).focus();
            handled = true;
        }
        if (
            !handled &&
            this._lastAutofocusedChatWindowLocalId === this.storeProps.autofocusChatWindowLocalId &&
            this._lastAutofocusedCounter !== this.storeProps.autofocusCounter
        ) {
            this._getChatWindowRef(this.storeProps.autofocusChatWindowLocalId).focus();
            handled = true;
        }
        if (
            !handled &&
            this._lastAutofocusedChatWindowLocalId !== this.storeProps.autofocusChatWindowLocalId
        ) {
            this._getChatWindowRef(this.storeProps.autofocusChatWindowLocalId).focus();
            handled = true;
        }
        this._lastAutofocusedChatWindowLocalId = this.storeProps.autofocusChatWindowLocalId;
        this._lastAutofocusedCounter = this.storeProps.autofocusCounter;
        this.storeDispatch('setChatWindowManagerNotifiedAutofocusCounter', this._lastAutofocusedCounter);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when a chat window asks to focus the next chat window.
     *
     * @private
     * @param {CustomEvent} ev
     * @param {string} ev.detail.currentChatWindowLocalId
     */
    _onFocusNextChatWindow(ev) {
        const orderedVisible = this.orderedVisible;
        if (orderedVisible.length === 1) {
            return;
        }

        const _getNextVisibleChatWindowIndex = index => {
            let nextIndex = index + 1;
            if (nextIndex > orderedVisible.length - 1) {
                nextIndex = 0;
            }
            return nextIndex;
        };

        const _getNextOpenVisibleChatWindowIndex = currentChatWindowIndex => {
            let nextIndex = _getNextVisibleChatWindowIndex(currentChatWindowIndex);
            let nextToFocusChatWindowLocalId = orderedVisible[nextIndex].chatWindowLocalId;
            while (this._getChatWindowRef(nextToFocusChatWindowLocalId).isFolded()) {
                nextIndex = _getNextVisibleChatWindowIndex(nextIndex);
                nextToFocusChatWindowLocalId = orderedVisible[nextIndex].chatWindowLocalId;
            }
            return nextIndex;
        };

        const currentChatWindowIndex = orderedVisible.findIndex(item =>
            item.chatWindowLocalId === ev.detail.currentChatWindowLocalId);
        const nextIndex = _getNextOpenVisibleChatWindowIndex(currentChatWindowIndex);
        this.storeDispatch('focusChatWindow', orderedVisible[nextIndex].chatWindowLocalId);
    }

    /**
     * TODO: almost duplicate code with
     *
     *  - Discuss._onRedirect()
     *
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {integer} ev.detail.id
     * @param {string} ev.detail.model
     */
    _onRedirect(ev) {
        this.storeDispatch('redirect', {
            ev,
            id: ev.detail.id,
            model: ev.detail.model,
        });
    }

    /**
     * Called when hidden menu asks to select a chat window, i.e. make it
     * visible.
     *
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.chatWindowLocalId
     */
    _onSelectChatWindow(ev) {
        this.storeDispatch('makeChatWindowVisible', ev.detail.chatWindowLocalId);
    }

    /**
     * Called when the 'new_message' chat window asks to select a chat window.
     * It should replace this 'new_message' chat window.
     *
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.chatWindowLocalId
     * @param {string} ev.detail.threadLocalId
     */
    _onSelectThreadChatWindow(ev) {
        const { chatWindowLocalId, threadLocalId } = ev.detail;
        if (!this.env.store.state.threads[threadLocalId].is_minimized) {
            this.storeDispatch('openThread', threadLocalId, { chatWindowMode: 'last' });
        }
        this.storeDispatch('replaceChatWindow', chatWindowLocalId, threadLocalId);
    }
}

ChatWindowManager.components = { ChatWindow, HiddenMenu };

ChatWindowManager.template = 'mail.component.ChatWindowManager';

return ChatWindowManager;

});
