odoo.define('mail.component.ChatWindowHiddenMenu', function (require) {
'use strict';

const ChatWindowHeader = require('mail.component.ChatWindowHeader');

class HiddenMenu extends owl.Component {

    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.id = _.uniqueId('o_chatWindowHiddenMenu_');
        this.state = owl.useState({
            isOpen: false,
        });
        this.storeProps = owl.hooks.useStore((state, props) => {
            return {
                threads: props.chatWindowLocalIds
                    .filter(chatWindowLocalId => chatWindowLocalId !== 'new_message')
                    .map(chatWindowLocalId => state.threads[chatWindowLocalId]),
            };
        });
        this._onClickCaptureGlobal = this._onClickCaptureGlobal.bind(this);
        this._listRef = owl.hooks.useRef('list');
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
        this._listRef.el.style['max-height'] = `${this.props.GLOBAL_HEIGHT / 2}px`;
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

HiddenMenu.props = {
    chatWindowLocalIds: {
        type: Array,
        element: String,
    },
    direction: {
        type: String,
        optional: true,
    },
    offset: Number,
};

HiddenMenu.template = 'mail.component.ChatWindowHiddenMenu';

return HiddenMenu;

});
