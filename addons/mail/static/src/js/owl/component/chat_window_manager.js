odoo.define('mail.component.ChatWindowManager', function (require) {
"use strict";

const ChatWindow = require('mail.component.ChatWindow');
const HiddenMenu = require('mail.component.ChatWindowHiddenMenu');

class ChatWindowManager extends owl.store.ConnectedComponent {

    /**
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.DEBUG = true;
        // others
        this.TEXT_DIRECTION = this.env._t.database.parameters.direction;
        this._lastAutofocusedCounter = 0;
        this._lastAutofocusedChatWindowLocalId = undefined;
        if (this.DEBUG) {
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
     * @param {integer} index
     * @return {boolean}
     */
    chatWindowShiftRight(index) {
        return index < this.storeProps.computed.visible.length - 1;
    }

    /**
     * Save the states of chat windows in the store that are related to a
     * thread. This includes scroll positions and composer state
     * (input content + attachments).
     */
    saveChatWindowsStates() {
        this.dispatch('saveChatWindowsStates', Object
            .entries(this.__owl__.refs)
            .reduce((acc, [refId, ref]) => {
                if (!refId.startsWith('chatWindow_')) {
                    return acc;
                }
                if (ref.props.chatWindowLocalId === 'new_message') {
                    return acc;
                }
                return {
                    ...acc,
                    [ref.props.chatWindowLocalId]: ref.getState(),
                };
            }, {})
        );
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @return {mail.component.ChatWindow}
     */
    _getChatWindowRef(chatWindowLocalId){
        return this.__owl__.refs[`chatWindow_${chatWindowLocalId}`];
    }

    /**
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
        this.dispatch('setChatWindowManagerNotifiedAutofocusCounter', this._lastAutofocusedCounter);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
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
        this.dispatch('focusChatWindow', orderedVisible[nextIndex].chatWindowLocalId);
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
        this.dispatch('redirect', {
            ev,
            id: ev.detail.id,
            model: ev.detail.model,
        });
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.chatWindowLocalId
     */
    _onSelectChatWindow(ev) {
        this.dispatch('makeChatWindowVisible', ev.detail.chatWindowLocalId);
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.chatWindowLocalId
     * @param {string} ev.detail.threadLocalId
     */
    _onSelectThreadChatWindow(ev) {
        const { chatWindowLocalId, threadLocalId } = ev.detail;
        if (!this.env.store.state.threads[threadLocalId].is_minimized) {
            this.dispatch('openThread', threadLocalId, { chatWindowMode: 'last' });
        }
        this.dispatch('replaceChatWindow', chatWindowLocalId, threadLocalId);
    }
}

ChatWindowManager.components = {
    ChatWindow,
    HiddenMenu,
};

/**
 * @param {Object} state
 * @return {Object}
 */
ChatWindowManager.mapStoreToProps = function (state) {
    const {
        autofocusCounter,
        autofocusChatWindowLocalId,
        computed,
        storedChatWindowStates,
    } = state.chatWindowManager;
    return {
        autofocusCounter,
        autofocusChatWindowLocalId,
        computed,
        isMobile: state.isMobile,
        storedChatWindowStates,
    };
};

ChatWindowManager.template = 'mail.component.ChatWindowManager';

return ChatWindowManager;

});
