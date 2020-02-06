odoo.define('mail.messaging.entity.ChatWindow', function (require) {
'use strict';

const { registerNewEntity } = require('mail.messaging.entity.core');

function ChatWindowFactory({ Entity }) {

    const BASE_VISUAL = {
        /**
         * Amount of visible slots available for chat windows.
         */
        availableVisibleSlots: 0,
        /**
         * Data related to the hidden menu.
         */
        hidden: {
            /**
             * List of hidden docked chat windows. Useful to compute counter.
             * Chat windows are ordered by their `chatWindows` order.
             */
            _chatWindows: [],
            /**
             * Whether hidden menu is visible or not
             */
            isVisible: false,
            /**
             * Offset of hidden menu starting point from the starting point
             * of chat window manager. Makes only sense if it is visible.
             */
            offset: 0,
        },
        /**
         * Data related to visible chat windows. Index determine order of
         * docked chat windows.
         *
         * Value:
         *
         *  {
         *      _chatWindow,
         *      offset,
         *  }
         *
         * Offset is offset of starting point of docked chat window from
         * starting point of dock chat window manager. Docked chat windows
         * are ordered by their `chatWindows` order
         */
        visible: [],
    };


    class ChatWindow extends Entity {

        /**
         * @override
         */
        static create(data) {
            const chatWindow = super.create(data);
            this.register(chatWindow);
            return chatWindow;
        }

        /**
         * @override
         */
        delete() {
            this.constructor.unregister(this);
            super.delete();
            if (this.thread) {
                this.thread.updateFoldState('closed');
            }
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @static
         * @returns {mail.messaging.entity.ChatWindow}
         */
        static get allOrdered() {
            return this._ordered.map(_chatWindow => this.get(_chatWindow));
        }

        /**
         * @static
         * @returns {mail.messaging.entity.ChatWindow[]}
         */
        static get allOrderedVisible() {
            return this.visual.visible.map(({ _chatWindow }) => this.get(_chatWindow));
        }

        /**
         * @static
         * @returns {mail.messaging.entity.ChatWindow[]}
         */
        static get allOrderedHidden() {
            return this.visual.hidden._chatWindows.map(_chatWindow => this.get(_chatWindow));
        }

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
         * @static
         * @returns {boolean}
         */
        static get hasHiddenChatWindows() {
            return this.visual.hidden._chatWindows.length > 0;
        }

        /**
         * @static
         * @returns {boolean}
         */
        static get hasVisibleChatWindows() {
            return this.visual.visible.length > 0;
        }

        /**
         * @static
         * @returns {mail.messaging.entity.ChatWindow|undefined}
         */
        static get lastVisible() {
            const { length: l, [l - 1]: lastVisible } = this.allOrderedVisible;
            return lastVisible;
        }

        /**
         * @static
         * @returns {mail.messaging.entity.ChatWindow|undefined}
         */
        static get newMessage() {
            return this.all.find(chatWindow => !chatWindow.thread);
        }

        /**
         * @static
         */
        static openNewMessage() {
            if (!this.newMessage) {
                this.create();
            }
            this.newMessage.makeVisible();
            this.newMessage.focus();
        }

        /**
         * @static
         * @param {mail.messaging.entity.Thread} thread
         * @param {Object} [param1={}]
         * @param {string} [param1.mode='last_visible']
         */
        static openThread(thread, { mode = 'last_visible' } = {}) {
            if (thread.foldState === 'closed') {
                thread.updateFoldState('open');
            }
            let chatWindow = this.fromThread(thread);
            if (!chatWindow) {
                chatWindow = this.create({ thread });
            }
            if (mode === 'last_visible' && !chatWindow.isVisible) {
                chatWindow.makeVisible();
            }
            if (mode === 'from_new_message') {
                const newMessage = this.newMessage;
                if (!newMessage) {
                    throw new Error('Cannot open thread in chat window in mode "from_new_message" without any new message chat window');
                }
                this.swap(chatWindow, newMessage);
                newMessage.close();
            }
            chatWindow.focus();
        }

        /**
         * @static
         * @param {mail.messaging.entity.ChatWindow} chatWindow
         */
        static register(chatWindow) {
            if (this.allOrdered.includes(chatWindow)) {
                return;
            }
            this.update({
                _ordered: this._ordered.concat([chatWindow.localId]),
            });
        }

        /**
         * Shift provided chat window to the left on screen.
         *
         * @static
         * @param {mail.messaging.entity.ChatWindow} chatWindow
         */
        static shiftLeft(chatWindow) {
            const chatWindows = this.allOrdered;
            const index = chatWindows.findIndex(cw => cw === chatWindow);
            if (index === chatWindows.length - 1) {
                // already left-most
                return;
            }
            const otherChatWindow = chatWindows[index + 1];
            const _newOrdered = [...this._ordered];
            _newOrdered[index] = otherChatWindow.localId;
            _newOrdered[index + 1] = chatWindow.localId;
            this.update({ _ordered: _newOrdered });
            chatWindow.focus();
        }

        /**
         * Shift provided chat window to the right on screen.
         *
         * @static
         * @param {mail.messaging.entity.ChatWindow} chatWindow
         */
        static shiftRight(chatWindow) {
            const chatWindows = this.allOrdered;
            const index = chatWindows.findIndex(cw => cw === chatWindow);
            if (index === 0) {
                // already right-most
                return;
            }
            const otherChatWindow = chatWindows[index - 1];
            const _newOrdered = [...this._ordered];
            _newOrdered[index] = otherChatWindow.localId;
            _newOrdered[index - 1] = chatWindow.localId;
            this.update({ _ordered: _newOrdered });
            chatWindow.focus();
        }

        /**
         * @static
         * @param {mail.messaging.entity.ChatWindow} chatWindow1
         * @param {mail.messaging.entity.ChatWindow} chatWindow2
         */
        static swap(chatWindow1, chatWindow2) {
            const ordered = this.allOrdered;
            const index1 = ordered.findIndex(chatWindow => chatWindow === chatWindow1);
            const index2 = ordered.findIndex(chatWindow => chatWindow === chatWindow2);
            if (index1 === -1 || index2 === -1) {
                return;
            }
            const _newOrdered = [...this._ordered];
            _newOrdered[index1] = chatWindow2.localId;
            _newOrdered[index2] = chatWindow1.localId;
            this.update({ _ordered: _newOrdered });
        }

        /**
         * @static
         */
        static toggleHiddenMenu() {
            this.update({ isHiddenMenuOpen: !this.isHiddenMenuOpen });
        }

        /**
         * @static
         * @returns {integer}
         */
        static get unreadHiddenConversationAmount() {
            const allHiddenWithThread = this.allOrderedHidden.filter(
                chatWindow => chatWindow.thread
            );
            let amount = 0;
            for (const chatWindow of allHiddenWithThread) {
                if (chatWindow.thread.message_unread_counter > 0) {
                    amount++;
                }
            }
            return amount;
        }

        /**
         * @static
         * @param {mail.messaging.entity.ChatWindow} chatWindow
         */
        static unregister(chatWindow) {
            if (!this.allOrdered.includes(chatWindow)) {
                return;
            }
            this.update({
                _ordered: this._ordered.filter(
                    _chatWindow => _chatWindow !== chatWindow.localId
                ),
            });
        }

        /**
         * @static
         * @returns {Object}
         */
        static get visual() {
            let visual = JSON.parse(JSON.stringify(BASE_VISUAL));
            if (!this.env.messaging || !this.env.messaging.isInitialized) {
                return visual;
            }
            const device = this.env.messaging.device;
            const discuss = this.env.messaging.discuss;
            const BETWEEN_GAP_WIDTH = 5;
            const CHAT_WINDOW_WIDTH = 325;
            const END_GAP_WIDTH = device.isMobile ? 0 : 10;
            const GLOBAL_WINDOW_WIDTH = device.globalWindowInnerWidth;
            const HIDDEN_MENU_WIDTH = 200; // max width, including width of dropup list items
            const START_GAP_WIDTH = device.isMobile ? 0 : 10;
            const chatWindows = this.allOrdered;
            if (!device.isMobile && discuss.isOpen) {
                return visual;
            }
            if (!chatWindows.length) {
                return visual;
            }
            const relativeGlobalWindowWidth = GLOBAL_WINDOW_WIDTH - START_GAP_WIDTH - END_GAP_WIDTH;
            let maxAmountWithoutHidden = Math.floor(
                relativeGlobalWindowWidth / (CHAT_WINDOW_WIDTH + BETWEEN_GAP_WIDTH));
            let maxAmountWithHidden = Math.floor(
                (relativeGlobalWindowWidth - HIDDEN_MENU_WIDTH - BETWEEN_GAP_WIDTH) /
                (CHAT_WINDOW_WIDTH + BETWEEN_GAP_WIDTH));
            if (device.isMobile) {
                maxAmountWithoutHidden = 1;
                maxAmountWithHidden = 1;
            }
            if (chatWindows.length <= maxAmountWithoutHidden) {
                // all visible
                for (let i = 0; i < chatWindows.length; i++) {
                    const _chatWindow = chatWindows[i].localId;
                    const offset = START_GAP_WIDTH + i * (CHAT_WINDOW_WIDTH + BETWEEN_GAP_WIDTH);
                    visual.visible.push({ _chatWindow, offset });
                }
                visual.availableVisibleSlots = maxAmountWithoutHidden;
            } else if (maxAmountWithHidden > 0) {
                // some visible, some hidden
                for (let i = 0; i < maxAmountWithHidden; i++) {
                    const _chatWindow = chatWindows[i].localId;
                    const offset = START_GAP_WIDTH + i * (CHAT_WINDOW_WIDTH + BETWEEN_GAP_WIDTH);
                    visual.visible.push({ _chatWindow, offset });
                }
                if (chatWindows.length > maxAmountWithHidden) {
                    visual.hidden.isVisible = !device.isMobile;
                    visual.hidden.offset = visual.visible[maxAmountWithHidden - 1].offset
                        + CHAT_WINDOW_WIDTH + BETWEEN_GAP_WIDTH;
                }
                for (let j = maxAmountWithHidden; j < chatWindows.length; j++) {
                    visual.hidden._chatWindows.push(chatWindows[j].localId);
                }
                visual.availableVisibleSlots = maxAmountWithHidden;
            } else {
                // all hidden
                visual.hidden.isVisible = !device.isMobile;
                visual.hidden.offset = START_GAP_WIDTH;
                visual.hidden._chatWindows.concat(chatWindows.map(chatWindow => chatWindow.localId));
                console.warn('cannot display any visible chat windows (screen is too small)');
                visual.availableVisibleSlots = 0;
            }
            return visual;
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
            const index = this.constructor.allOrderedVisible.findIndex(visible => visible === this);
            if (index === -1) {
                return false;
            }
            return index > 0;
        }

        /**
         * @returns {boolean}
         */
        get hasShiftRight() {
            const allVisible = this.constructor.allOrderedVisible;
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
            const lastVisible = this.constructor.lastVisible;
            this.constructor.swap(this, lastVisible);
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
            this.constructor.shiftLeft(this);
        }

        /**
         * Shift this chat window to the right on screen.
         */
        shiftRight() {
            this.constructor.shiftRight(this);
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
            const visible = this.constructor.visual.visible;
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
         * @override
         */
        static _getListOfClassAttributeNames() {
            return super._getListOfClassAttributeNames().concat([
                '_ordered',
                'isHiddenMenuOpen',
            ]);
        }

        /**
         * @override
         */
        static _update(data) {
            const {
                /**
                 * List of ordered chat windows (list of local ids)
                 */
                _ordered = this._ordered || [],
                isHiddenMenuOpen = this.isHiddenMenuOpen || false,
            } = data;

            this._write({
                _ordered,
                isHiddenMenuOpen,
            });
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
         */
        _cycleNextVisibleUnfoldedChatWindow({ reverse = false } = {}) {
            const orderedVisible = this.constructor.allOrderedVisible;
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
                thread: threadOrLocalId,
                /**
                 * If set, this is the scroll top position of the thread of this
                 * chat window to put initially on mount.
                 */
                threadInitialScrollTop = this.threadInitialScrollTop,
            } = data;

            const thread = this.env.entities.Thread.get(threadOrLocalId);

            const prevThread = this.thread;

            this._write({
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
                this._write({ threadInitialScrollTop: undefined });
            }
        }

    }

    Object.assign(ChatWindow, {
        relations: Object.assign({}, Entity.relations, {
            threadViewer: {
                inverse: 'chatWindow',
                to: 'ThreadViewer',
                type: 'one2one',
            },
        }),
    });

    return ChatWindow;
}

registerNewEntity('ChatWindow', ChatWindowFactory);

});
