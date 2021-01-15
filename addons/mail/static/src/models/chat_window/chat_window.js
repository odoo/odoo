odoo.define('mail/static/src/models/chat_window/chat_window.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2one, one2many, one2one } = require('mail/static/src/model/model_field.js');
const { clear } = require('mail/static/src/model/model_field_command.js');

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
         * @param {boolean} [param0.notifyServer]
         */
        close({ notifyServer } = {}) {
            if (notifyServer === undefined) {
                notifyServer = !this.env.messaging.device.isMobile;
            }
            const thread = this.thread;
            this.delete();
            // Flux specific: 'closed' fold state should only be saved on the
            // server when manually closing the chat window. Delete at destroy
            // or sync from server value for example should not save the value.
            if (thread && notifyServer) {
                thread.notifyFoldStateToServer('closed');
            }
            if (this.env.device.isMobile && !this.env.messaging.discuss.isOpen) {
                // If we are in mobile and discuss is not open, it means the
                // chat window was opened from the messaging menu. In that
                // case it should be re-opened to simulate it was always
                // there in the background.
                this.env.messaging.messagingMenu.update({ isOpen: true });
            }
        }

        expand() {
            if (this.thread) {
                this.thread.open({ expanded: true });
            }
        }

        /**
         * Programmatically auto-focus an existing chat window.
         */
        focus() {
            this.update({ isDoFocus: true });
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
         * @param {boolean} [param0.notifyServer]
         */
        fold({ notifyServer } = {}) {
            if (notifyServer === undefined) {
                notifyServer = !this.env.messaging.device.isMobile;
            }
            this.update({ isFolded: true });
            // Flux specific: manually folding the chat window should save the
            // new state on the server.
            if (this.thread && notifyServer) {
                this.thread.notifyFoldStateToServer('folded');
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
            if (this.isVisible) {
                return;
            }
            const lastVisible = this.manager.lastVisible;
            this.manager.swap(this, lastVisible);
        }

        /**
         * Shift this chat window to the left on screen.
         */
        shiftLeft() {
            this.manager.shiftLeft(this);
        }

        /**
         * Shift this chat window to the right on screen.
         */
        shiftRight() {
            this.manager.shiftRight(this);
        }

        /**
         * @param {Object} [param0={}]
         * @param {boolean} [param0.notifyServer]
         */
        unfold({ notifyServer } = {}) {
            if (notifyServer === undefined) {
                notifyServer = !this.env.messaging.device.isMobile;
            }
            this.update({ isFolded: false });
            // Flux specific: manually opening the chat window should save the
            // new state on the server.
            if (this.thread && notifyServer) {
                this.thread.notifyFoldStateToServer('open');
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
            return this.isVisible && !this.isFolded && !this.thread;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasShiftLeft() {
            if (!this.manager) {
                return false;
            }
            const allVisible = this.manager.allOrderedVisible;
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
            if (!this.manager) {
                return false;
            }
            const index = this.manager.allOrderedVisible.findIndex(visible => visible === this);
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
            return this.isVisible && !this.isFolded && this.thread;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsFolded() {
            const thread = this.thread;
            if (thread) {
                return thread.foldState === 'folded';
            }
            return this.isFolded;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsVisible() {
            if (!this.manager) {
                return false;
            }
            return this.manager.allOrderedVisible.includes(this);
        }

        /**
         * @private
         * @returns {string}
         */
        _computeName() {
            if (this.thread) {
                return this.thread.displayName;
            }
            return this.env._t("New message");
        }

        /**
         * @private
         * @returns {integer|undefined}
         */
        _computeVisibleIndex() {
            if (!this.manager) {
                return clear();
            }
            const visible = this.manager.visual.visible;
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
            if (!this.manager) {
                return 0;
            }
            const visible = this.manager.visual.visible;
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
            const orderedVisible = this.manager.allOrderedVisible;
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
            if (!this.threadView) {
                return;
            }
            this.threadView.addComponentHint('home-menu-hidden');
        }

        /**
         * @private
         */
        async _onShowHomeMenu() {
            if (!this.threadView) {
                return;
            }
            this.threadView.addComponentHint('home-menu-shown');
        }

    }

    ChatWindow.fields = {
        /**
         * Determines whether "new message form" should be displayed.
         */
        hasNewMessageForm: attr({
            compute: '_computeHasNewMessageForm',
            dependencies: [
                'isFolded',
                'isVisible',
                'thread',
            ],
        }),
        hasShiftLeft: attr({
            compute: '_computeHasShiftLeft',
            dependencies: ['managerAllOrderedVisible'],
            default: false,
        }),
        hasShiftRight: attr({
            compute: '_computeHasShiftRight',
            dependencies: ['managerAllOrderedVisible'],
            default: false,
        }),
        /**
         * Determines whether `this.thread` should be displayed.
         */
        hasThreadView: attr({
            compute: '_computeHasThreadView',
            dependencies: [
                'isFolded',
                'isVisible',
                'thread',
            ],
        }),
        /**
         * Determine whether the chat window should be programmatically
         * focused by observed component of chat window. Those components
         * are responsible to unmark this record afterwards, otherwise
         * any re-render will programmatically set focus again!
         */
        isDoFocus: attr({
            default: false,
        }),
        /**
         * States whether `this` is focused. Useful for visual clue.
         */
        isFocused: attr({
            default: false,
        }),
        /**
         * Determines whether `this` is folded.
         */
        isFolded: attr({
            default: false,
        }),
        /**
         * States whether `this` is visible or not. Should be considered
         * read-only. Setting this value manually will not make it visible.
         * @see `makeVisible`
         */
        isVisible: attr({
            compute: '_computeIsVisible',
            dependencies: [
                'managerAllOrderedVisible',
            ],
        }),
        manager: many2one('mail.chat_window_manager', {
            inverse: 'chatWindows',
        }),
        managerAllOrderedVisible: one2many('mail.chat_window', {
            related: 'manager.allOrderedVisible',
        }),
        managerVisual: attr({
            related: 'manager.visual',
        }),
        name: attr({
            compute: '_computeName',
            dependencies: [
                'thread',
                'threadDisplayName',
            ],
        }),
        /**
         * Determines the `mail.thread` that should be displayed by `this`.
         * If no `mail.thread` is linked, `this` is considered "new message".
         */
        thread: one2one('mail.thread', {
            inverse: 'chatWindow',
        }),
        threadDisplayName: attr({
            related: 'thread.displayName',
        }),
        /**
         * States the `mail.thread_view` displaying `this.thread`.
         */
        threadView: one2one('mail.thread_view', {
            related: 'threadViewer.threadView',
        }),
        /**
         * Determines the `mail.thread_viewer` managing the display of `this.thread`.
         */
        threadViewer: one2one('mail.thread_viewer', {
            default: [['create']],
            inverse: 'chatWindow',
            isCausal: true,
        }),
        /**
         * This field handle the "order" (index) of the visible chatWindow inside the UI.
         *
         * Using LTR, the right-most chat window has index 0, and the number is incrementing from right to left.
         * Using RTL, the left-most chat window has index 0, and the number is incrementing from left to right.
         */
        visibleIndex: attr({
            compute: '_computeVisibleIndex',
            dependencies: [
                'manager',
                'managerVisual',
            ],
        }),
        visibleOffset: attr({
            compute: '_computeVisibleOffset',
            dependencies: ['managerVisual'],
        }),
    };

    ChatWindow.modelName = 'mail.chat_window';

    return ChatWindow;
}

registerNewModel('mail.chat_window', factory);

});
