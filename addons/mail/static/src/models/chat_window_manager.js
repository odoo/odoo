/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insertAndReplace, link, replace } from '@mail/model/model_field_command';

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

registerModel({
    name: 'ChatWindowManager',
    identifyingFields: ['messaging'],
    recordMethods: {
        /**
         * Close all chat windows.
         *
         */
        closeAll() {
            const chatWindows = this.allOrdered;
            for (const chatWindow of chatWindows) {
                chatWindow.close();
            }
        },
        closeHiddenMenu() {
            this.update({ isHiddenMenuOpen: false });
        },
        /**
         * Closes all chat windows related to the given thread.
         *
         * @param {Thread} thread
         * @param {Object} [options]
         */
        closeThread(thread, options) {
            for (const chatWindow of this.chatWindows) {
                if (chatWindow.thread === thread) {
                    chatWindow.close(options);
                }
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickHiddenMenuToggler(ev) {
            if (this.isHiddenMenuOpen) {
                this.closeHiddenMenu();
            } else {
                this.openHiddenMenu();
            }
        },
        openHiddenMenu() {
            this.update({ isHiddenMenuOpen: true });
        },
        openNewMessage() {
            if (!this.newMessageChatWindow) {
                this.update({ newMessageChatWindow: insertAndReplace({ manager: replace(this) }) });
            }
            this.newMessageChatWindow.makeActive();
        },
        /**
         * @param {Thread} thread
         * @param {Object} [param1={}]
         * @param {boolean} [param1.focus] if set, set focus the chat window
         *   to open.
         * @param {boolean} [param1.isFolded=false]
         * @param {boolean} [param1.makeActive=false]
         * @param {boolean} [param1.notifyServer]
         * @param {boolean} [param1.replaceNewMessage=false]
         */
        openThread(thread, {
            focus,
            isFolded = false,
            makeActive = false,
            notifyServer,
            replaceNewMessage = false
        } = {}) {
            if (notifyServer === undefined) {
                notifyServer = !this.messaging.device.isSmall;
            }
            let chatWindow = thread.chatWindow;
            if (!chatWindow) {
                chatWindow = this.messaging.models['ChatWindow'].create({
                    isFolded,
                    manager: replace(this),
                    thread: replace(thread),
                });
            } else {
                chatWindow.update({ isFolded });
            }
            if (replaceNewMessage && this.newMessageChatWindow) {
                this.swap(chatWindow, this.newMessageChatWindow);
                this.newMessageChatWindow.close();
            }
            if (makeActive) {
                // avoid double notify at this step, it will already be done at
                // the end of the current method
                chatWindow.makeActive({ focus, notifyServer: false });
            }
            // Flux specific: notify server of chat window being opened.
            if (notifyServer && !this.messaging.currentGuest) {
                const foldState = chatWindow.isFolded ? 'folded' : 'open';
                thread.notifyFoldStateToServer(foldState);
            }
        },
        /**
         * Shift provided chat window to previous visible index, which swap visible order of this
         * chat window and the preceding visible one
         *
         * @param {ChatWindow} chatWindow
         */
        shiftPrev(chatWindow) {
            const chatWindows = this.allOrdered;
            const index = chatWindows.findIndex(cw => cw === chatWindow);
            if (index === chatWindows.length - 1) {
                // already first one
                return;
            }
            const otherChatWindow = chatWindows[index + 1];
            const _newOrdered = [...this.allOrdered];
            _newOrdered[index] = otherChatWindow;
            _newOrdered[index + 1] = chatWindow;
            this.update({ allOrdered: replace(_newOrdered) });
            chatWindow.focus();
            for (const loopedChatWindow of [chatWindow, otherChatWindow]) {
                if (loopedChatWindow.threadView) {
                    loopedChatWindow.threadView.addComponentHint('adjust-scroll');
                }
            }
        },
        /**
         * Shift provided chat window to next visible index, which swap visible order of this
         * chat window and the following visible one.
         *
         * @param {ChatWindow} chatWindow
         */
        shiftNext(chatWindow) {
            const chatWindows = this.allOrdered;
            const index = chatWindows.findIndex(cw => cw === chatWindow);
            if (index === 0) {
                // already last one
                return;
            }
            const otherChatWindow = chatWindows[index - 1];
            const _newOrdered = [...this.allOrdered];
            _newOrdered[index] = otherChatWindow;
            _newOrdered[index - 1] = chatWindow;
            this.update({ allOrdered: replace(_newOrdered) });
            chatWindow.focus();
            for (const loopedChatWindow of [chatWindow, otherChatWindow]) {
                if (loopedChatWindow.threadView) {
                    loopedChatWindow.threadView.addComponentHint('adjust-scroll');
                }
            }
        },
        /**
         * @param {ChatWindow} chatWindow1
         * @param {ChatWindow} chatWindow2
         */
        swap(chatWindow1, chatWindow2) {
            const ordered = this.allOrdered;
            const index1 = ordered.findIndex(chatWindow => chatWindow === chatWindow1);
            const index2 = ordered.findIndex(chatWindow => chatWindow === chatWindow2);
            if (index1 === -1 || index2 === -1) {
                return;
            }
            const _newOrdered = [...this.allOrdered];
            _newOrdered[index1] = chatWindow2;
            _newOrdered[index2] = chatWindow1;
            this.update({ allOrdered: replace(_newOrdered) });
            for (const chatWindow of [chatWindow1, chatWindow2]) {
                if (chatWindow.threadView) {
                    chatWindow.threadView.addComponentHint('adjust-scroll');
                }
            }
        },
        /**
         * @private
         * @returns {ChatWindow[]}
         */
        _computeAllOrdered() {
            return link(this.chatWindows);
        },
        /**
         * @private
         * @returns {ChatWindow[]}
         */
        _computeAllOrderedHidden() {
            return replace(this.visual.hidden.chatWindowLocalIds.map(chatWindowLocalId =>
                this.messaging.models['ChatWindow'].get(chatWindowLocalId)
            ));
        },
        /**
         * @private
         * @returns {ChatWindow[]}
         */
        _computeAllOrderedVisible() {
            return replace(this.visual.visible.map(({ chatWindowLocalId }) =>
                this.messaging.models['ChatWindow'].get(chatWindowLocalId)
            ));
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasVisibleChatWindows() {
            return this.allOrderedVisible.length > 0;
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeHiddenChatWindowHeaderViews() {
            if (this.allOrderedHidden.length > 0) {
                return insertAndReplace(this.allOrderedHidden.map(chatWindow => ({ chatWindowOwner: replace(chatWindow) })));
            }
            return clear();
        },
        /**
         * @private
         * @returns {ChatWindow|undefined}
         */
        _computeLastVisible() {
            const { length: l, [l - 1]: lastVisible } = this.allOrderedVisible;
            if (!lastVisible) {
                return clear();
            }
            return replace(lastVisible);
        },
        /**
         * @private
         * @returns {integer}
         */
        _computeUnreadHiddenConversationAmount() {
            const allHiddenWithThread = this.allOrderedHidden.filter(
                chatWindow => chatWindow.thread
            );
            let amount = 0;
            for (const chatWindow of allHiddenWithThread) {
                if (chatWindow.thread.localMessageUnreadCounter > 0) {
                    amount++;
                }
            }
            return amount;
        },
        /**
         * @private
         * @returns {Object}
         */
        _computeVisual() {
            let visual = JSON.parse(JSON.stringify(BASE_VISUAL));
            if (!this.messaging || !this.messaging.device) {
                return visual;
            }
            const BETWEEN_GAP_WIDTH = 5;
            const CHAT_WINDOW_WIDTH = 325;
            const END_GAP_WIDTH = this.messaging.device.isSmall ? 0 : 10;
            const HIDDEN_MENU_WIDTH = 200; // max width, including width of dropup list items
            const START_GAP_WIDTH = this.messaging.device.isSmall ? 0 : 10;
            if (!this.messaging.device.isSmall && this.messaging.discuss.discussView) {
                return visual;
            }
            if (!this.allOrdered.length) {
                return visual;
            }
            const relativeGlobalWindowWidth = this.messaging.device.globalWindowInnerWidth - START_GAP_WIDTH - END_GAP_WIDTH;
            let maxAmountWithoutHidden = Math.floor(
                relativeGlobalWindowWidth / (CHAT_WINDOW_WIDTH + BETWEEN_GAP_WIDTH));
            let maxAmountWithHidden = Math.floor(
                (relativeGlobalWindowWidth - HIDDEN_MENU_WIDTH - BETWEEN_GAP_WIDTH) /
                (CHAT_WINDOW_WIDTH + BETWEEN_GAP_WIDTH));
            if (this.messaging.device.isSmall) {
                maxAmountWithoutHidden = 1;
                maxAmountWithHidden = 1;
            }
            if (this.allOrdered.length <= maxAmountWithoutHidden) {
                // all visible
                for (let i = 0; i < this.allOrdered.length; i++) {
                    const chatWindowLocalId = this.allOrdered[i].localId;
                    const offset = START_GAP_WIDTH + i * (CHAT_WINDOW_WIDTH + BETWEEN_GAP_WIDTH);
                    visual.visible.push({ chatWindowLocalId, offset });
                }
                visual.availableVisibleSlots = maxAmountWithoutHidden;
            } else if (maxAmountWithHidden > 0) {
                // some visible, some hidden
                for (let i = 0; i < maxAmountWithHidden; i++) {
                    const chatWindowLocalId = this.allOrdered[i].localId;
                    const offset = START_GAP_WIDTH + i * (CHAT_WINDOW_WIDTH + BETWEEN_GAP_WIDTH);
                    visual.visible.push({ chatWindowLocalId, offset });
                }
                if (this.allOrdered.length > maxAmountWithHidden) {
                    visual.hidden.isVisible = !this.messaging.device.isSmall;
                    visual.hidden.offset = visual.visible[maxAmountWithHidden - 1].offset
                        + CHAT_WINDOW_WIDTH + BETWEEN_GAP_WIDTH;
                }
                for (let j = maxAmountWithHidden; j < this.allOrdered.length; j++) {
                    visual.hidden.chatWindowLocalIds.push(this.allOrdered[j].localId);
                }
                visual.availableVisibleSlots = maxAmountWithHidden;
            } else {
                // all hidden
                visual.hidden.isVisible = !this.messaging.device.isSmall;
                visual.hidden.offset = START_GAP_WIDTH;
                visual.hidden.chatWindowLocalIds.concat(this.allOrdered.map(chatWindow => chatWindow.localId));
                console.warn('cannot display any visible chat windows (screen is too small)');
                visual.availableVisibleSlots = 0;
            }
            return visual;
        },
    },
    fields: {
        /**
         * List of ordered chat windows.
         */
        allOrdered: many('ChatWindow', {
            compute: '_computeAllOrdered',
        }),
        allOrderedHidden: many('ChatWindow', {
            compute: '_computeAllOrderedHidden',
        }),
        allOrderedVisible: many('ChatWindow', {
            compute: '_computeAllOrderedVisible',
        }),
        chatWindows: many('ChatWindow', {
            inverse: 'manager',
            isCausal: true,
        }),
        hasVisibleChatWindows: attr({
            compute: '_computeHasVisibleChatWindows',
        }),
        hiddenChatWindowHeaderViews: many('ChatWindowHeaderView', {
            compute: '_computeHiddenChatWindowHeaderViews',
        }),
        isHiddenMenuOpen: attr({
            default: false,
        }),
        lastVisible: one('ChatWindow', {
            compute: '_computeLastVisible',
        }),
        newMessageChatWindow: one('ChatWindow', {
            inverse: 'managerAsNewMessage',
            isCausal: true,
        }),
        unreadHiddenConversationAmount: attr({
            compute: '_computeUnreadHiddenConversationAmount',
        }),
        visual: attr({
            compute: '_computeVisual',
            default: BASE_VISUAL,
        }),
    },
});
