odoo.define('mail.component.ChatWindowHiddenMenu', function (require) {
"use strict";

const ChatWindowHeader = require('mail.component.ChatWindowHeader');

class HiddenMenu extends owl.store.ConnectedComponent {

    /**
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.id = _.uniqueId('o_chatWindowHiddenMenu_');
        this.state = owl.useState({
            isOpen: false,
        });
        this._globalCaptureClickEventListener = ev => this._onClickCaptureGlobal(ev);
        this._listRef = owl.hooks.useRef('list');
    }

    mounted() {
        this._apply();
        document.addEventListener('click', this._globalCaptureClickEventListener, true);
    }

    patched() {
        this._apply();
    }

    willUnmount() {
        document.removeEventListener('click', this._globalCaptureClickEventListener, true);
    }

    //--------------------------------------------------------------------------
    // Getter / Setter
    //--------------------------------------------------------------------------

    /**
     * @return {integer}
     */
    get unreadCounter() {
        return this.storeProps.threads.reduce((count, thread) => {
            count += thread.message_unread_counter > 0 ? 1 : 0;
            return count;
        }, 0);
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
        this._listRef.el.style['max-height'] = `${this.props.GLOBAL_HEIGHT/2}px`;
    }

    /**
     * @private
     */
    _applyOffset() {
        const offsetFrom = this.props.direction === 'rtl' ? 'right' : 'left';
        const oppositeFrom = offsetFrom === 'right' ? 'left' : 'right';
        this.el.style[offsetFrom] = `${this.props.offset}px`;
        this.el.style[oppositeFrom] = 'auto';
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickCaptureGlobal(ev) {
        if (ev.target === this.el) {
            return;
        }
        if (ev.target.closest(`[data-id="${this.id}"]`)) {
            return;
        }
        this.state.isOpen = false;
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickToggle(ev) {
        this.state.isOpen = !this.state.isOpen;
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.chatWindowLocalId
     */
    _onCloseChatWindow(ev) {
        this.trigger('o-close-chat-window', {
            chatWindowLocalId: ev.detail.chatWindowLocalId,
        });
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.chatWindowLocalId
     */
    _onClickedChatWindow(ev) {
        this.trigger('o-select-chat-window', {
            chatWindowLocalId: ev.detail.chatWindowLocalId,
        });
        this.state.isOpen = false;
    }
}

HiddenMenu.components = {
    ChatWindowHeader,
};

HiddenMenu.defaultProps = {
    direction: 'rtl',
};

/**
 * @param {Object} state
 * @param {Object} ownProps
 * @param {string[]} ownProps.chatWindowLocalIds
 * @return {Object}
 */
HiddenMenu.mapStoreToProps = function (state, ownProps) {
    return {
        threads: ownProps.chatWindowLocalIds
            .filter(chatWindowLocalId => chatWindowLocalId !== 'new_message')
            .map(chatWindowLocalId => state.threads[chatWindowLocalId]),
    };
};

HiddenMenu.props = {
    chatWindowLocalIds: {
        type: Array,
        element: String,
    },
    direction: String,
    offset: Number,
    threads: {
        type: Array,
        element: Object, // {mail.store.model.Thread}
    },
};

HiddenMenu.template = 'mail.component.ChatWindowHiddenMenu';

return HiddenMenu;

});
