odoo.define('mail/static/src/models/chat_window/chat_window.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { clear } = require('mail/static/src/model/model_field_command.js');
const { attr, many2one, one2many, one2one } = require('mail/static/src/model/model_field_utils.js');

function factory(dependencies) {

    class ChatWindow extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            const res = super._created(...arguments);
            this._onShowHomeMenu.bind(this);
            this._onHideHomeMenu.bind(this);

            this.env.messagingBus.on('hide_home_menu', this, this._onHideHomeMenu);
            this.env.messagingBus.on('show_home_menu', this, this._onShowHomeMenu);
            return res;
        }

        /**
         * @override
         */
        _willDelete() {
            this.env.messagingBus.off('hide_home_menu', this, this._onHideHomeMenu);
            this.env.messagingBus.off('show_home_menu', this, this._onShowHomeMenu);
            return super._willDelete(...arguments);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Close this chat window.
         *
         * @param {Object} [param0={}]
         * @param {boolean} [param0.notifyServer=true]
         */
        close({ notifyServer = true } = {}) {
            const thread = this.__mfield_thread(this);
            this.delete();
            // Flux specific: 'closed' fold state should only be saved on the
            // server when manually closing the chat window. Delete at destroy
            // or sync from server value for example should not save the value.
            if (thread && notifyServer) {
                thread.notifyFoldStateToServer('closed');
            }
        }

        expand() {
            if (this.__mfield_thread(this)) {
                this.__mfield_thread(this).open({ expanded: true });
            }
        }

        /**
         * Programmatically auto-focus an existing chat window.
         */
        focus() {
            this.update({
                __mfield_isDoFocus: true,
            });
        }

        focusNextVisibleUnfoldedChatWindow() {
            const nextVisibleUnfoldedChatWindow = this._getNextVisibleUnfoldedChatWindow();
            if (nextVisibleUnfoldedChatWindow) {
                nextVisibleUnfoldedChatWindow.focus();
            }
        }

        focusPreviousVisibleUnfoldedChatWindow() {
            const previousVisibleUnfoldedChatWindow =
                this._getNextVisibleUnfoldedChatWindow({ reverse: true });
            if (previousVisibleUnfoldedChatWindow) {
                previousVisibleUnfoldedChatWindow.focus();
            }
        }

        /**
         * @param {Object} [param0={}]
         * @param {boolean} [param0.notifyServer=true]
         */
        fold({ notifyServer = true } = {}) {
            this.update({ __mfield_isFolded: true });
            // Flux specific: manually folding the chat window should save the
            // new state on the server.
            if (this.__mfield_thread(this) && notifyServer) {
                this.__mfield_thread(this).notifyFoldStateToServer('folded');
            }
        }

        /**
         * Makes this chat window active, which consists of making it visible,
         * unfolding it, and focusing it.
         *
         * @param {Object} [options]
         */
        makeActive(options) {
            this.makeVisible();
            this.unfold(options);
            this.focus();
        }

        /**
         * Makes this chat window visible by swapping it with the last visible
         * chat window, or do nothing if it is already visible.
         */
        makeVisible() {
            if (this.__mfield_isVisible(this)) {
                return;
            }
            const lastVisible = this.__mfield_manager(this).__mfield_lastVisible(this);
            this.__mfield_manager(this).swap(this, lastVisible);
        }

        /**
         * Shift this chat window to the left on screen.
         */
        shiftLeft() {
            this.__mfield_manager(this).shiftLeft(this);
        }

        /**
         * Shift this chat window to the right on screen.
         */
        shiftRight() {
            this.__mfield_manager(this).shiftRight(this);
        }

        /**
         * @param {Object} [param0={}]
         * @param {boolean} [param0.notifyServer=true]
         */
        unfold({ notifyServer = true } = {}) {
            this.update({ __mfield_isFolded: false });
            // Flux specific: manually opening the chat window should save the
            // new state on the server.
            if (this.__mfield_thread(this) && notifyServer) {
                this.__mfield_thread(this).notifyFoldStateToServer('open');
            }
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasNewMessageForm() {
            return (
                this.__mfield_isVisible(this) &&
                !this.__mfield_isFolded(this) &&
                !this.__mfield_thread(this)
            );
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasShiftLeft() {
            if (!this.__mfield_manager(this)) {
                return false;
            }
            const allVisible = this.__mfield_manager(this).__mfield_allOrderedVisible(this);
            const index = allVisible.findIndex(visible => visible === this);
            if (index === -1) {
                return false;
            }
            return index < allVisible.length - 1;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasShiftRight() {
            if (!this.__mfield_manager(this)) {
                return false;
            }
            const index = this.__mfield_manager(this).__mfield_allOrderedVisible(this).findIndex(visible => visible === this);
            if (index === -1) {
                return false;
            }
            return index > 0;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasThreadView() {
            return (
                this.__mfield_isVisible(this) &&
                !this.__mfield_isFolded(this) &&
                this.__mfield_thread(this)
            );
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsFolded() {
            const thread = this.__mfield_thread(this);
            if (thread) {
                return thread.__mfield_foldState(this) === 'folded';
            }
            return this.__mfield_isFolded(this);
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsVisible() {
            if (!this.__mfield_manager(this)) {
                return false;
            }
            return this.__mfield_manager(this).__mfield_allOrderedVisible(this).includes(this);
        }

        /**
         * @private
         * @returns {string}
         */
        _computeName() {
            if (this.__mfield_thread(this)) {
                return this.__mfield_thread(this).__mfield_displayName(this);
            }
            return this.env._t("New message");
        }

        /**
         * @private
         * @returns {integer|undefined}
         */
        _computeVisibleIndex() {
            if (!this.__mfield_manager(this)) {
                return clear();
            }
            const visible = this.__mfield_manager(this).__mfield_visual(this).visible;
            const index = visible.findIndex(visible => visible.chatWindowLocalId === this.localId);
            if (index === -1) {
                return clear();
            }
            return index;
        }

        /**
         * @private
         * @returns {integer}
         */
        _computeVisibleOffset() {
            if (!this.__mfield_manager(this)) {
                return 0;
            }
            const visible = this.__mfield_manager(this).__mfield_visual(this).visible;
            const index = visible.findIndex(visible => visible.chatWindowLocalId === this.localId);
            if (index === -1) {
                return 0;
            }
            return visible[index].offset;
        }

        /**
         * Cycles to the next possible visible and unfolded chat window starting
         * from the `currentChatWindow`, following the natural order based on the
         * current text direction, and with the possibility to `reverse` based on
         * the given parameter.
         *
         * @private
         * @param {Object} [param0={}]
         * @param {boolean} [param0.reverse=false]
         * @returns {mail.chat_window|undefined}
         */
        _getNextVisibleUnfoldedChatWindow({ reverse = false } = {}) {
            const orderedVisible = this.__mfield_manager(this).__mfield_allOrderedVisible(this);
            /**
             * Return index of next visible chat window of a given visible chat
             * window index. The direction of "next" chat window depends on
             * `reverse` option.
             *
             * @param {integer} index
             * @returns {integer}
             */
            const _getNextIndex = index => {
                const directionOffset = reverse ? 1 : -1;
                let nextIndex = index + directionOffset;
                if (nextIndex > orderedVisible.length - 1) {
                    nextIndex = 0;
                }
                if (nextIndex < 0) {
                    nextIndex = orderedVisible.length - 1;
                }
                return nextIndex;
            };

            const currentIndex = orderedVisible.findIndex(visible => visible === this);
            let nextIndex = _getNextIndex(currentIndex);
            let nextToFocus = orderedVisible[nextIndex];
            while (nextToFocus.isFolded) {
                nextIndex = _getNextIndex(nextIndex);
                nextToFocus = orderedVisible[nextIndex];
            }
            return nextToFocus;
        }

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

        /**
         * @private
         */
        async _onHideHomeMenu() {
            if (!this.__mfield_threadView(this)) {
                return;
            }
            this.__mfield_threadView(this).addComponentHint('home-menu-hidden');
        }

        /**
         * @private
         */
        async _onShowHomeMenu() {
            if (!this.__mfield_threadView(this)) {
                return;
            }
            this.__mfield_threadView(this).addComponentHint('home-menu-shown');
        }

    }

    ChatWindow.fields = {
        /**
         * Determines whether "new message form" should be displayed.
         */
        __mfield_hasNewMessageForm: attr({
            compute: '_computeHasNewMessageForm',
            dependencies: [
                '__mfield_isFolded',
                '__mfield_isVisible',
                '__mfield_thread',
            ],
        }),
        __mfield_hasShiftLeft: attr({
            compute: '_computeHasShiftLeft',
            dependencies: [
                '__mfield_managerAllOrderedVisible',
            ],
            default: false,
        }),
        __mfield_hasShiftRight: attr({
            compute: '_computeHasShiftRight',
            dependencies: [
                '__mfield_managerAllOrderedVisible',
            ],
            default: false,
        }),
        /**
         * Determines whether `this.thread` should be displayed.
         */
        __mfield_hasThreadView: attr({
            compute: '_computeHasThreadView',
            dependencies: [
                '__mfield_isFolded',
                '__mfield_isVisible',
                '__mfield_thread',
            ],
        }),
        /**
         * Determine whether the chat window should be programmatically
         * focused by observed component of chat window. Those components
         * are responsible to unmark this record afterwards, otherwise
         * any re-render will programmatically set focus again!
         */
        __mfield_isDoFocus: attr({
            default: false,
        }),
        /**
         * States whether `this` is focused. Useful for visual clue.
         */
        __mfield_isFocused: attr({
            default: false,
        }),
        /**
         * Determines whether `this` is folded.
         */
        __mfield_isFolded: attr({
            default: false,
        }),
        /**
         * States whether `this` is visible or not. Should be considered
         * read-only. Setting this value manually will not make it visible.
         * @see `makeVisible`
         */
        __mfield_isVisible: attr({
            compute: '_computeIsVisible',
            dependencies: [
                '__mfield_managerAllOrderedVisible',
            ],
        }),
        __mfield_manager: many2one('mail.chat_window_manager', {
            inverse: '__mfield_chatWindows',
        }),
        __mfield_managerAllOrderedVisible: one2many('mail.chat_window', {
            related: '__mfield_manager.__mfield_allOrderedVisible',
        }),
        __mfield_managerVisual: attr({
            related: '__mfield_manager.__mfield_visual',
        }),
        __mfield_name: attr({
            compute: '_computeName',
            dependencies: [
                '__mfield_thread',
                '__mfield_threadDisplayName',
            ],
        }),
        /**
         * Determines the `mail.thread` that should be displayed by `this`.
         * If no `mail.thread` is linked, `this` is considered "new message".
         */
        __mfield_thread: one2one('mail.thread', {
            inverse: '__mfield_chatWindow',
        }),
        __mfield_threadDisplayName: attr({
            related: '__mfield_thread.__mfield_displayName',
        }),
        /**
         * States the `mail.thread_view` displaying `this.thread`.
         */
        __mfield_threadView: one2one('mail.thread_view', {
            related: '__mfield_threadViewer.__mfield_threadView',
        }),
        /**
         * Determines the `mail.thread_viewer` managing the display of `this.thread`.
         */
        __mfield_threadViewer: one2one('mail.thread_viewer', {
            default: [['create']],
            inverse: '__mfield_chatWindow',
            isCausal: true,
        }),
        /**
         * This field handle the "order" (index) of the visible chatWindow inside the UI.
         *
         * Using LTR, the right-most chat window has index 0, and the number is incrementing from right to left.
         * Using RTL, the left-most chat window has index 0, and the number is incrementing from left to right.
         */
        __mfield_visibleIndex: attr({
            compute: '_computeVisibleIndex',
            dependencies: [
                '__mfield_manager',
                '__mfield_managerVisual',
            ],
        }),
        __mfield_visibleOffset: attr({
            compute: '_computeVisibleOffset',
            dependencies: [
                '__mfield_managerVisual',
            ],
        }),
    };

    ChatWindow.modelName = 'mail.chat_window';

    return ChatWindow;
}

registerNewModel('mail.chat_window', factory);

});
