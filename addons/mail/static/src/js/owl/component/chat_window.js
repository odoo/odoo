odoo.define('mail.component.ChatWindow', function (require) {
'use strict';

const AutocompleteInput = require('mail.component.AutocompleteInput');
const Header = require('mail.component.ChatWindowHeader');
const Thread = require('mail.component.Thread');

class ChatWindow extends owl.Component {

    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.id = _.uniqueId('o_chatWindow_');
        this.state = owl.useState({
            focused: false,
            folded: false, // used for 'new_message' chat window
        });
        this.storeDispatch = owl.hooks.useDispatch();
        this.storeGetters = owl.hooks.useGetters();
        this.storeProps = owl.hooks.useStore((state, props) => {
            return {
                isMobile: state.isMobile,
                thread: state.threads[props.chatWindowLocalId],
            };
        });
        this._inputRef = owl.hooks.useRef('input');
        this._threadRef = owl.hooks.useRef('thread');

        // the following are passed as props to children
        this._onAutocompleteSelect = this._onAutocompleteSelect.bind(this);
        this._onAutocompleteSource = this._onAutocompleteSource.bind(this);
    }

    mounted() {
        if (this.props.isDocked) {
            this._applyDockOffset();
        }
    }

    patched() {
        if (this.props.isDocked) {
            this._applyDockOffset();
        }
    }

    //--------------------------------------------------------------------------
    // Getter / Setter
    //--------------------------------------------------------------------------

    /**
     * @return {string}
     */
    get newMessageFormInputPlaceholder() {
        return this.env._t("Search user...");
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    focus() {
        this.state.focused = true;
        if (!this.storeProps.thread) {
            this._inputRef.comp.focus();
        } else {
            this._threadRef.comp.focus();
        }
    }

    /**
     * Get the state of the chat window. Chat windows that have no thread do
     * not have any state, hence it returns `undefined`.
     *
     * @return {Object|undefined} with format:
     *  {
     *      composerAttachmentLocalIds: {Array},
     *      composerTextInputHtmlContent: {String},
     *      scrollTop: {integer}
     *  }
     */
    getState() {
        if (!this._threadRef.comp) {
            return;
        }
        const {
            attachmentLocalIds: composerAttachmentLocalIds,
            textInputHtmlContent: composerTextInputHtmlContent
        } = this._threadRef.comp.getComposerState();
        return {
            composerAttachmentLocalIds,
            composerTextInputHtmlContent,
            scrollTop: this._threadRef.comp.getScrollTop()
        };
    }

    /**
     * @return {boolean}
     */
    isFolded() {
        if (this.storeProps.thread) {
            return this.storeProps.thread.state === 'folded';
        }
        return this.state.folded;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _applyDockOffset() {
        const offsetFrom = this.props.dockDirection === 'rtl' ? 'right' : 'left';
        const oppositeFrom = offsetFrom === 'right' ? 'left' : 'right';
        this.el.style[offsetFrom] = this.props.dockOffset + 'px';
        this.el.style[oppositeFrom] = 'auto';
    }

    /**
     * @private
     */
    _focusout() {
        this.state.focused = false;
        if (!this.storeProps.thread) {
            this._inputRef.comp.focusout();
        } else {
            this._threadRef.comp.focusout();
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     * @param {Object} ui
     * @param {Object} ui.item
     * @param {integer} ui.item.id
     */
    _onAutocompleteSelect(ev, ui) {
        const partnerId = ui.item.id;
        const partnerLocalId = `res.partner_${partnerId}`;
        const chat = this.storeGetters.chatFromPartner(partnerLocalId);
        if (chat) {
            this.trigger('o-select-thread', {
                chatWindowLocalId: this.props.chatWindowLocalId,
                threadLocalId: chat.localId,
            });
        } else {
            this.storeDispatch('closeChatWindow', this.props.chatWindowLocalId);
            this.storeDispatch('createChannel', {
                autoselect: true,
                partnerId,
                type: 'chat'
            });
        }
    }

    /**
     * @private
     * @param {Object} req
     * @param {string} req.term
     * @param {function} res
     */
    _onAutocompleteSource(req, res) {
        return this.storeDispatch('searchPartners', {
            callback: (partners) => {
                const suggestions = partners.map(partner => {
                    return {
                        id: partner.id,
                        value: this.storeGetters.partnerName(partner.localId),
                        label: this.storeGetters.partnerName(partner.localId),
                    };
                });
                res(_.sortBy(suggestions, 'label'));
            },
            keyword: _.escape(req.term),
            limit: 10,
        });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        if (this.state.focused && !this.isFolded()) {
            return;
        }
        if (this.isFolded()) {
            this.state.focused = true; // focus chat window but not input
        } else {
            this.focus();
        }
    }

    /**
     * @private
     * @param {CustomEvent} ev
     */
    _onClickedHeader(ev) {
        if (this.storeProps.isMobile) {
            return;
        }
        if (!this.storeProps.thread) {
            this.state.folded = !this.state.folded;
        } else {
            this.storeDispatch('toggleFoldThread', this.props.chatWindowLocalId);
        }
    }

    /**
     * @private
     * @param {FocusEvent} ev
     */
    _onFocusinThread(ev) {
        this.state.focused = true;
    }

    /**
     * Prevent auto-focus of fuzzy search in the home menu.
     * Useful in order to allow copy/paste content inside chat window with
     * CTRL-C & CTRL-V when on the home menu.
     *
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydown(ev) {
        ev.stopPropagation();
        if (ev.key === 'Tab') {
            ev.preventDefault();
            this.trigger('o-focus-next-chat-window', {
                currentChatWindowLocalId: this.props.chatWindowLocalId,
            });
        }
    }

}

ChatWindow.components = {
    AutocompleteInput,
    Header,
    Thread,
};

ChatWindow.defaultProps = {
    dockDirection: 'rtl',
    dockOffset: 0,
    hasCloseAsBackButton: false,
    hasShiftLeft: false,
    hasShiftRight: false,
    isDocked: false,
    isExpandable: false,
    isFullscreen: false,
};

ChatWindow.props = {
    chatWindowLocalId: String,
    composerInitialAttachmentLocalIds: {
        type: Array,
        element: String,
        optional: true,
    },
    composerInitialTextInputHtmlContent: {
        type: String,
        optional: true,
    },
    dockDirection: String,
    dockOffset: Number,
    hasCloseAsBackButton: Boolean,
    hasShiftLeft: Boolean,
    hasShiftRight: Boolean,
    isDocked: Boolean,
    isExpandable: Boolean,
    isFullscreen: Boolean,
    threadInitialScrollTop: {
        type: Number,
        optional: true,
    },
};

ChatWindow.template = 'mail.component.ChatWindow';

return ChatWindow;

});
