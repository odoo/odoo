odoo.define('mail.messaging.entity.ChatWindow', function (require) {
'use strict';

const {
    fields: {
        many2one,
        one2one,
    },
    registerNewEntity,
} = require('mail.messaging.entity.core');

function ChatWindowFactory({ Entity }) {

    class ChatWindow extends Entity {

        /**
         * @override
         */
        delete() {
            if (this.manager) {
                this.manager.unregister(this);
            }
            const thread = this.thread;
            super.delete();
            if (thread) {
                thread.updateFoldState('closed');
            }
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Close all chat windows.
         *
         * @static
         */
        static closeAll() {
            const chatWindows = this.all;
            for (const chatWindow of chatWindows) {
                chatWindow.close();
            }
        }

        /**
         * @static
         * @param {mail.messaging.entity.Thread} thread
         * @returns {mail.messaging.entity.ChatWindow|undefined}
         */
        static fromThread(thread) {
            return this.all.find(chatWindow => chatWindow.thread === thread);
        }

        /**
         * Close this chat window.
         */
        close() {
            this.delete();
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
            this.update({
                isDoFocus: true,
                isFocused: true,
            });
        }

        focusNextVisibleUnfoldedChatWindow() {
            const nextVisibleUnfoldedChatWindow = this._cycleNextVisibleUnfoldedChatWindow();
            nextVisibleUnfoldedChatWindow.focus();
        }

        focusPreviousVisibleUnfoldedChatWindow() {
            const previousVisibleUnfoldedChatWindow =
                this._cycleNextVisibleUnfoldedChatWindow({ reverse: true });
            previousVisibleUnfoldedChatWindow.focus();
        }

        /**
         * @returns {boolean}
         */
        get hasShiftLeft() {
            const index = this.manager.allOrderedVisible.findIndex(visible => visible === this);
            if (index === -1) {
                return false;
            }
            return index > 0;
        }

        /**
         * @returns {boolean}
         */
        get hasShiftRight() {
            const allVisible = this.manager.allOrderedVisible;
            const index = allVisible.findIndex(visible => visible === this);
            if (index === -1) {
                return false;
            }
            return index < allVisible.length - 1;
        }

        /**
         * @returns {boolean}
         */
        get isFolded() {
            const thread = this.thread;
            if (thread) {
                return thread.foldState === 'folded';
            }
            return this._isFolded;
        }

        /**
         * Assume that this chat window was hidden before-hand
         */
        makeVisible() {
            const lastVisible = this.manager.lastVisible;
            this.manager.swap(this, lastVisible);
        }

        /**
         * @returns {string}
         */
        get name() {
            if (this.thread) {
                return this.thread.displayName;
            }
            return this.env._t("New message");
        }

        /**
         * Shift provided chat window to the left on screen.
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
         * @returns {mail.messaging.entity.Thread|undefined}
         */
        get thread() {
            return this.threadViewer && this.threadViewer.thread;
        }

        toggleFold() {
            if (this.thread) {
                this.thread.updateFoldState(this.thread.foldState === 'folded' ? 'open' : 'folded');
            } else {
                this.update({ _isFolded: !this._isFolded });
            }
        }

        /**
         * @returns {integer}
         */
        get visibleOffset() {
            const visible = this.manager.visual.visible;
            const index = visible.findIndex(visible => visible._chatWindow === this.localId);
            if (index === -1) {
                return 0;
            }
            return visible[index].offset;
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * Cycles to the next possible visible and unfolded chat window starting
         * from the `currentChatWindow`, following the natural order based on the
         * current text direction, and with the possibility to `reverse` based on
         * the given parameter.
         *
         * @private
         * @param {Object} [param0={}]
         * @param {boolean} [param0.reverse=false]
         */
        _cycleNextVisibleUnfoldedChatWindow({ reverse = false } = {}) {
            const orderedVisible = this.manager.allOrderedVisible;
            if (orderedVisible.length <= 1) {
                return;
            }

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
            nextToFocus.focus();
        }

        /**
         * @override
         * @param {string|mail.messaging.entity.Thread} [data.thread]
         */
        _update(data) {
            const {
                /**
                 * Determine whether the chat window is folded or not, when not
                 * linked to a thread.
                 */
                _isFolded = this._isFolded || false,
                isDoFocus,
                /**
                 * Determine whether the chat window is focused or not. Useful for
                 * visual clue.
                 */
                isFocused = this.isFocused || false,
                manager,
                thread: threadOrLocalId,
                /**
                 * If set, this is the scroll top position of the thread of this
                 * chat window to put initially on mount.
                 */
                threadInitialScrollTop = this.threadInitialScrollTop,
            } = data;

            const thread = this.env.entities.Thread.get(threadOrLocalId);

            const prevManager = this.manager;
            const prevThread = this.thread;

            Object.assign(this, {
                /**
                 * Note: this value only make sense for chat window not linked
                 * to a thread. State of chat window of a thread is entirely
                 * based on thread.foldState. @see isFolded getter.
                 */
                _isFolded,
                /**
                 * Determine whether the chat window should be programmatically
                 * focused by observed component of chat window. Those components
                 * are responsible to unmark this entity afterwards, otherwise
                 * any re-render will programmatically set focus again!
                 */
                isDoFocus: isDoFocus || isFocused || this.isDoFocus,
                isFocused,
                threadInitialScrollTop,
            });

            // manager
            if (manager && this.manager !== manager) {
                manager.register(this);
                if (prevManager) {
                    prevManager.unregister(this);
                }
            }
            // thread
            if (thread && this.thread !== thread) {
                if (!this.threadViewer) {
                    const threadViewer = this.env.entities.ThreadViewer.create();
                    this.link({ threadViewer });
                }
                this.threadViewer.update({ thread });
                if (prevThread) {
                    prevThread.updateFoldState('closed');
                }
                this.threadInitialScrollTop = undefined;
            }
        }

    }

    ChatWindow.fields = {
        manager: many2one('ChatWindowManager', {
            inverse: 'chatWindows',
        }),
        threadViewer: one2one('ThreadViewer'),
    };

    return ChatWindow;
}

registerNewEntity('ChatWindow', ChatWindowFactory);

});
