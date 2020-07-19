odoo.define('mail/static/src/models/chat_window/chat_window.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2one, one2many, one2one } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    class ChatWindow extends dependencies['mail.model'] {

        /**
         * @override
         */
        static create(data) {
            const chatWindow = super.create(data);
            chatWindow._onShowHomeMenu.bind(chatWindow);
            chatWindow._onHideHomeMenu.bind(chatWindow)

            chatWindow.env.messagingBus.on(
                'hide_home_menu',
                chatWindow,
                chatWindow._onHideHomeMenu
            );
            chatWindow.env.messagingBus.on(
                'show_home_menu',
                chatWindow,
                chatWindow._onShowHomeMenu
            );
            return chatWindow;
        }

        /**
         * @override
         */
        delete() {
            this.env.messagingBus.off('hide_home_menu', this, this._onHideHomeMenu);
            this.env.messagingBus.off('show_home_menu', this, this._onShowHomeMenu);
            super.delete();
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Close this chat window.
         */
        close() {
            const thread = this.thread;
            this.delete();
            if (thread) {
                thread.update({ pendingFoldState: 'closed' });
            }
        }

        expand() {
            if (this.thread) {
                this.thread.openExpanded();
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

        fold() {
            if (this.thread) {
                this.thread.update({ pendingFoldState: 'folded' });
            } else {
                this.update({ _isFolded: true });
            }
        }

        /**
         * Assume that this chat window was hidden before-hand.
         */
        makeVisible() {
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

        unfold() {
            if (this.thread) {
                this.thread.update({ pendingFoldState: 'open' });
                this.threadViewer.addComponentHint('chat-window-unfolded');
            } else {
                this.update({ _isFolded: false });
            }
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

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
        _computeIsFolded() {
            const thread = this.thread;
            if (thread) {
                return thread.foldState === 'folded';
            }
            return this._isFolded;
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
                const directionOffset = reverse ? -1 : 1;
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
            if (!this.threadViewer) {
                return;
            }
            this.threadViewer.addComponentHint('home-menu-hidden');
        }

        /**
         * @private
         */
        async _onShowHomeMenu() {
            if (!this.threadViewer) {
                return;
            }
            this.threadViewer.addComponentHint('home-menu-shown');
        }

    }

    ChatWindow.fields = {
        /**
         * Determine whether the chat window is folded or not, when not
         * linked to a thread.
         * Note: this value only make sense for chat window not linked
         * to a thread. State of chat window of a thread is entirely
         * based on thread.foldState. @see isFolded .
         */
        _isFolded: attr({
            default: false,
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
         * Determine whether the chat window should be programmatically
         * focused by observed component of chat window. Those components
         * are responsible to unmark this record afterwards, otherwise
         * any re-render will programmatically set focus again!
         */
        isDoFocus: attr({
            default: false,
        }),
        /**
         * Determine whether the chat window is focused or not. Useful for
         * visual clue.
         */
        isFocused: attr({
            default: false,
        }),
        isFolded: attr({
            compute: '_computeIsFolded',
            dependencies: [
                'thread',
                'threadFoldState',
                '_isFolded',
            ],
            default: false,
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
        thread: many2one('mail.thread', {
            related: 'threadViewer.thread',
        }),
        threadDisplayName: attr({
            related: 'thread.displayName',
        }),
        threadFoldState: attr({
            related: 'thread.foldState',
        }),
        threadViewer: one2one('mail.thread_viewer', {
            inverse: 'chatWindow',
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
