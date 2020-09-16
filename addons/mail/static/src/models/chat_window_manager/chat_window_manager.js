odoo.define('mail/static/src/models/chat_window_manager/chat_window_manager.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2one, one2many, one2one } = require('mail/static/src/model/model_field_utils.js');

function factory(dependencies) {

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
            chatWindowLocalIds: [],
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
         *      chatWindowLocalId,
         *      offset,
         *  }
         *
         * Offset is offset of starting point of docked chat window from
         * starting point of dock chat window manager. Docked chat windows
         * are ordered by their `chatWindows` order
         */
        visible: [],
    };


    class ChatWindowManager extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Close all chat windows.
         *
         */
        closeAll() {
            const chatWindows = this.__mfield_allOrdered(this);
            for (const chatWindow of chatWindows) {
                chatWindow.close();
            }
        }

        closeHiddenMenu() {
            this.update({
                __mfield_isHiddenMenuOpen: false,
            });
        }

        /**
         * Closes all chat windows related to the given thread.
         *
         * @param {mail.thread} thread
         * @param {Object} [options]
         */
        closeThread(thread, options) {
            for (const chatWindow of this.__mfield_chatWindows(this)) {
                if (chatWindow.__mfield_thread(this) === thread) {
                    chatWindow.close(options);
                }
            }
        }

        openHiddenMenu() {
            this.update({
                __mfield_isHiddenMenuOpen: true,
            });
        }

        openNewMessage() {
            let newMessageChatWindow = this.__mfield_newMessageChatWindow(this);
            if (!newMessageChatWindow) {
                newMessageChatWindow = this.env.models['mail.chat_window'].create({
                    __mfield_manager: [['link', this]],
                });
            }
            newMessageChatWindow.makeActive();
        }

        /**
         * @param {mail.thread} thread
         * @param {Object} [param1={}]
         * @param {boolean} [param1.isFolded=false]
         * @param {boolean} [param1.makeActive=false]
         * @param {boolean} [param1.notifyServer=true]
         * @param {boolean} [param1.replaceNewMessage=false]
         */
        openThread(thread, {
            isFolded = false,
            makeActive = false,
            notifyServer = true,
            replaceNewMessage = false
        } = {}) {
            let chatWindow = this.__mfield_chatWindows(this).find(chatWindow =>
                chatWindow.__mfield_thread(this) === thread
            );
            if (!chatWindow) {
                chatWindow = this.env.models['mail.chat_window'].create({
                    __mfield_isFolded: isFolded,
                    __mfield_manager: [['link', this]],
                    __mfield_thread: [['link', thread]],
                });
            } else {
                chatWindow.update({ __mfield_isFolded: isFolded });
            }
            if (replaceNewMessage && this.__mfield_newMessageChatWindow(this)) {
                this.swap(chatWindow, this.__mfield_newMessageChatWindow(this));
                this.__mfield_newMessageChatWindow(this).close();
            }
            if (makeActive) {
                // avoid double notify at this step, it will already be done at
                // the end of the current method
                chatWindow.makeActive({ notifyServer: false });
            }
            // Flux specific: notify server of chat window being opened.
            if (notifyServer) {
                const foldState = chatWindow.__mfield_isFolded(this) ? 'folded' : 'open';
                thread.notifyFoldStateToServer(foldState);
            }
        }

        /**
         * Shift provided chat window to the left on screen.
         *
         * @param {mail.chat_window} chatWindow
         */
        shiftLeft(chatWindow) {
            const chatWindows = this.__mfield_allOrdered(this);
            const index = chatWindows.findIndex(cw => cw === chatWindow);
            if (index === chatWindows.length - 1) {
                // already left-most
                return;
            }
            const otherChatWindow = chatWindows[index + 1];
            const _newOrdered = [...this.__mfield__ordered(this)];
            _newOrdered[index] = otherChatWindow.localId;
            _newOrdered[index + 1] = chatWindow.localId;
            this.update({
                __mfield__ordered: _newOrdered,
            });
            chatWindow.focus();
        }

        /**
         * Shift provided chat window to the right on screen.
         *
         * @param {mail.chat_window} chatWindow
         */
        shiftRight(chatWindow) {
            const chatWindows = this.__mfield_allOrdered(this);
            const index = chatWindows.findIndex(cw => cw === chatWindow);
            if (index === 0) {
                // already right-most
                return;
            }
            const otherChatWindow = chatWindows[index - 1];
            const _newOrdered = [...this.__mfield__ordered(this)];
            _newOrdered[index] = otherChatWindow.localId;
            _newOrdered[index - 1] = chatWindow.localId;
            this.update({
                __mfield__ordered: _newOrdered,
            });
            chatWindow.focus();
        }

        /**
         * @param {mail.chat_window} chatWindow1
         * @param {mail.chat_window} chatWindow2
         */
        swap(chatWindow1, chatWindow2) {
            const ordered = this.__mfield_allOrdered(this);
            const index1 = ordered.findIndex(chatWindow => chatWindow === chatWindow1);
            const index2 = ordered.findIndex(chatWindow => chatWindow === chatWindow2);
            if (index1 === -1 || index2 === -1) {
                return;
            }
            const _newOrdered = [...this.__mfield__ordered(this)];
            _newOrdered[index1] = chatWindow2.localId;
            _newOrdered[index2] = chatWindow1.localId;
            this.update({
                __mfield__ordered: _newOrdered,
            });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {string[]}
         */
        _compute_ordered() {
            // remove unlinked chatWindows
            const _ordered = this.__mfield__ordered(this).filter(chatWindowLocalId =>
                this.__mfield_chatWindows(this).includes(this.env.models['mail.chat_window'].get(chatWindowLocalId))
            );
            // add linked chatWindows
            for (const chatWindow of this.__mfield_chatWindows(this)) {
                if (!_ordered.includes(chatWindow.localId)) {
                    _ordered.push(chatWindow.localId);
                }
            }
            return _ordered;
        }

        /**
         * // FIXME: dependent on implementation that uses arbitrary order in relations!!
         *
         * @private
         * @returns {mail.chat_window}
         */
        _computeAllOrdered() {
            return [['replace', this.__mfield__ordered(this).map(chatWindowLocalId =>
                this.env.models['mail.chat_window'].get(chatWindowLocalId)
            )]];
        }

        /**
         * @private
         * @returns {mail.chat_window[]}
         */
        _computeAllOrderedHidden() {
            return [['replace', this.__mfield_visual(this).hidden.chatWindowLocalIds.map(chatWindowLocalId =>
                this.env.models['mail.chat_window'].get(chatWindowLocalId)
            )]];
        }

        /**
         * @private
         * @returns {mail.chat_window[]}
         */
        _computeAllOrderedVisible() {
            return [['replace', this.__mfield_visual(this).visible.map(({ chatWindowLocalId }) =>
                this.env.models['mail.chat_window'].get(chatWindowLocalId)
            )]];
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasHiddenChatWindows() {
            return this.__mfield_allOrderedHidden(this).length > 0;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasVisibleChatWindows() {
            return this.__mfield_allOrderedVisible(this).length > 0;
        }

        /**
         * @private
         * @returns {mail.chat_window|undefined}
         */
        _computeLastVisible() {
            const { length: l, [l - 1]: lastVisible } = this.__mfield_allOrderedVisible(this);
            if (!lastVisible) {
                return [['unlink']];
            }
            return [['link', lastVisible]];
        }

        /**
         * @private
         * @returns {mail.chat_window|undefined}
         */
        _computeNewMessageChatWindow() {
            const chatWindow = this.__mfield_allOrdered(this).find(chatWindow => !chatWindow.__mfield_thread(this));
            if (!chatWindow) {
                return [['unlink']];
            }
            return [['link', chatWindow]];
        }

        /**
         * @private
         * @returns {integer}
         */
        _computeUnreadHiddenConversationAmount() {
            const allHiddenWithThread = this.__mfield_allOrderedHidden(this).filter(
                chatWindow => chatWindow.__mfield_thread(this)
            );
            let amount = 0;
            for (const chatWindow of allHiddenWithThread) {
                if (chatWindow.__mfield_thread(this).__mfield_localMessageUnreadCounter(this) > 0) {
                    amount++;
                }
            }
            return amount;
        }

        /**
         * @private
         * @returns {Object}
         */
        _computeVisual() {
            let visual = JSON.parse(JSON.stringify(BASE_VISUAL));
            if (!this.env.messaging) {
                return visual;
            }
            const device = this.env.messaging.__mfield_device(this);
            const discuss = this.env.messaging.__mfield_discuss(this);
            const BETWEEN_GAP_WIDTH = 5;
            const CHAT_WINDOW_WIDTH = 325;
            const END_GAP_WIDTH = device.__mfield_isMobile(this) ? 0 : 10;
            const GLOBAL_WINDOW_WIDTH = device.__mfield_globalWindowInnerWidth(this);
            const HIDDEN_MENU_WIDTH = 200; // max width, including width of dropup list items
            const START_GAP_WIDTH = device.__mfield_isMobile(this) ? 0 : 10;
            const chatWindows = this.__mfield_allOrdered(this);
            if (!device.__mfield_isMobile(this) && discuss.__mfield_isOpen(this)) {
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
                    const chatWindowLocalId = chatWindows[i].localId;
                    const offset = START_GAP_WIDTH + i * (CHAT_WINDOW_WIDTH + BETWEEN_GAP_WIDTH);
                    visual.visible.push({ chatWindowLocalId, offset });
                }
                visual.availableVisibleSlots = maxAmountWithoutHidden;
            } else if (maxAmountWithHidden > 0) {
                // some visible, some hidden
                for (let i = 0; i < maxAmountWithHidden; i++) {
                    const chatWindowLocalId = chatWindows[i].localId;
                    const offset = START_GAP_WIDTH + i * (CHAT_WINDOW_WIDTH + BETWEEN_GAP_WIDTH);
                    visual.visible.push({ chatWindowLocalId, offset });
                }
                if (chatWindows.length > maxAmountWithHidden) {
                    visual.hidden.isVisible = !device.isMobile;
                    visual.hidden.offset = visual.visible[maxAmountWithHidden - 1].offset
                        + CHAT_WINDOW_WIDTH + BETWEEN_GAP_WIDTH;
                }
                for (let j = maxAmountWithHidden; j < chatWindows.length; j++) {
                    visual.hidden.chatWindowLocalIds.push(chatWindows[j].localId);
                }
                visual.availableVisibleSlots = maxAmountWithHidden;
            } else {
                // all hidden
                visual.hidden.isVisible = !device.isMobile;
                visual.hidden.offset = START_GAP_WIDTH;
                visual.hidden.chatWindowLocalIds.concat(chatWindows.map(chatWindow => chatWindow.localId));
                console.warn('cannot display any visible chat windows (screen is too small)');
                visual.availableVisibleSlots = 0;
            }
            return visual;
        }

    }

    ChatWindowManager.fields = {
        /**
         * List of ordered chat windows (list of local ids)
         */
        __mfield__ordered: attr({
            compute: '_compute_ordered',
            default: [],
            dependencies: [
                '__mfield_chatWindows',
            ],
        }),
        // FIXME: dependent on implementation that uses arbitrary order in relations!!
        __mfield_allOrdered: one2many('mail.chat_window', {
            compute: '_computeAllOrdered',
            dependencies: [
                '__mfield__ordered',
            ],
        }),
        __mfield_allOrderedThread: one2many('mail.thread', {
            related: '__mfield_allOrdered.__mfield_thread',
        }),
        __mfield_allOrderedHidden: one2many('mail.chat_window', {
            compute: '_computeAllOrderedHidden',
            dependencies: [
                '__mfield_visual',
            ],
        }),
        __mfield_allOrderedHiddenThread: one2many('mail.thread', {
            related: '__mfield_allOrderedHidden.__mfield_thread',
        }),
        __mfield_allOrderedHiddenThreadMessageUnreadCounter: attr({
            related: '__mfield_allOrderedHiddenThread.__mfield_localMessageUnreadCounter',
        }),
        __mfield_allOrderedVisible: one2many('mail.chat_window', {
            compute: '_computeAllOrderedVisible',
            dependencies: [
                '__mfield_visual',
            ],
        }),
        __mfield_chatWindows: one2many('mail.chat_window', {
            inverse: '__mfield_manager',
            isCausal: true,
        }),
        __mfield_device: one2one('mail.device', {
            related: '__mfield_messaging.__mfield_device',
        }),
        __mfield_deviceGlobalWindowInnerWidth: attr({
            related: '__mfield_device.__mfield_globalWindowInnerWidth',
        }),
        __mfield_deviceIsMobile: attr({
            related: '__mfield_device.__mfield_isMobile',
        }),
        __mfield_discuss: one2one('mail.discuss', {
            related: '__mfield_messaging.__mfield_discuss',
        }),
        __mfield_discussIsOpen: attr({
            related: '__mfield_discuss.__mfield_isOpen',
        }),
        __mfield_hasHiddenChatWindows: attr({
            compute: '_computeHasHiddenChatWindows',
            dependencies: [
                '__mfield_allOrderedHidden',
            ],
        }),
        __mfield_hasVisibleChatWindows: attr({
            compute: '_computeHasVisibleChatWindows',
            dependencies: [
                '__mfield_allOrderedVisible',
            ],
        }),
        __mfield_isHiddenMenuOpen: attr({
            default: false,
        }),
        __mfield_lastVisible: many2one('mail.chat_window', {
            compute: '_computeLastVisible',
            dependencies: [
                '__mfield_allOrderedVisible',
            ],
        }),
        __mfield_messaging: one2one('mail.messaging', {
            inverse: '__mfield_chatWindowManager',
        }),
        __mfield_newMessageChatWindow: one2one('mail.chat_window', {
            compute: '_computeNewMessageChatWindow',
            dependencies: [
                '__mfield_allOrderedThread',
            ],
        }),
        __mfield_unreadHiddenConversationAmount: attr({
            compute: '_computeUnreadHiddenConversationAmount',
            dependencies: [
                '__mfield_allOrderedHiddenThreadMessageUnreadCounter',
            ],
        }),
        __mfield_visual: attr({
            compute: '_computeVisual',
            default: BASE_VISUAL,
            dependencies: [
                '__mfield_allOrdered',
                '__mfield_deviceGlobalWindowInnerWidth',
                '__mfield_deviceIsMobile',
                '__mfield_discussIsOpen',
            ],
        }),
    };

    ChatWindowManager.modelName = 'mail.chat_window_manager';

    return ChatWindowManager;
}

registerNewModel('mail.chat_window_manager', factory);

});
