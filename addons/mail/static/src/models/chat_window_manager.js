/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

export const BASE_VISUAL = {
    /**
     * @deprecated, should use ChatWindowManager/availableVisibleSlots instead
     * Amount of visible slots available for chat windows.
     */
    availableVisibleSlots: 0,
    /**
     * List of hidden docked chat windows. Useful to compute counter.
     * Chat windows are ordered by their `chatWindows` order.
     */
    hiddenChatWindows: [],
    /**
     * Whether hidden menu is visible or not
     */
    isHiddenMenuVisible: false,
    /**
     * Offset of hidden menu starting point from the starting point
     * of chat window manager. Makes only sense if it is visible.
     */
    hiddenMenuOffset: 0,
    /**
     * Data related to visible chat windows. Index determine order of
     * docked chat windows.
     *
     * Value:
     *
     *  {
     *      chatWindow,
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
    recordMethods: {
        /**
         * Close all chat windows.
         *
         */
        closeAll() {
            for (const chatWindow of this.chatWindows) {
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
                this.update({ newMessageChatWindow: { manager: this } });
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
                chatWindow = this.messaging.models['ChatWindow'].insert({
                    isFolded,
                    manager: this,
                    thread,
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
         * @param {ChatWindow} chatWindow1
         * @param {ChatWindow} chatWindow2
         */
        swap(chatWindow1, chatWindow2) {
            const index1 = this.chatWindows.findIndex(chatWindow => chatWindow === chatWindow1);
            const index2 = this.chatWindows.findIndex(chatWindow => chatWindow === chatWindow2);
            if (index1 === -1 || index2 === -1) {
                return;
            }
            const _newOrdered = [...this.chatWindows];
            _newOrdered[index1] = chatWindow2;
            _newOrdered[index2] = chatWindow1;
            this.update({ chatWindows: _newOrdered });
            for (const chatWindow of [chatWindow1, chatWindow2]) {
                if (chatWindow.threadView) {
                    chatWindow.threadView.addComponentHint('adjust-scroll');
                }
            }
        },
    },
    fields: {
        allOrderedHidden: many('ChatWindow', {
            compute() {
                return this.visual.hiddenChatWindows;
            },
        }),
        allOrderedVisible: many('ChatWindow', {
            compute() {
                return this.visual.visible.map(({ chatWindow }) => chatWindow);
            },
        }),
        /**
         * Amount of visible slots available for chat windows.
         */
        availableVisibleSlots: attr({
            compute() {
                return this.visual.availableVisibleSlots;
            },
            default: 0,
        }),
        betweenGapWidth: attr({
            default: 5,
        }),
        chatWindows: many('ChatWindow', {
            inverse: 'manager',
            isCausal: true,
        }),
        chatWindowWidth: attr({
            default: 340,
        }),
        endGapWidth: attr({
            compute() {
                if (this.messaging.device.isSmall) {
                    return 0;
                }
                return 10;
            },
        }),
        hasVisibleChatWindows: attr({
            compute() {
                return this.allOrderedVisible.length > 0;
            },
        }),
        hiddenChatWindowHeaderViews: many('ChatWindowHeaderView', {
            compute() {
                if (this.allOrderedHidden.length > 0) {
                    return this.allOrderedHidden.map(chatWindow => ({ chatWindowOwner: chatWindow }));
                }
                return clear();
            },
        }),
        hiddenMenuWidth: attr({
            default: 170, // max width, including width of dropup list items
        }),
        isHiddenMenuOpen: attr({
            default: false,
        }),
        lastVisible: one('ChatWindow', {
            compute() {
                const { length: l, [l - 1]: lastVisible } = this.allOrderedVisible;
                if (!lastVisible) {
                    return clear();
                }
                return lastVisible;
            },
        }),
        newMessageChatWindow: one('ChatWindow', {
            inverse: 'managerAsNewMessage',
        }),
        startGapWidth: attr({
            compute() {
                if (this.messaging.device.isSmall) {
                    return 0;
                }
                return 10;
            },
        }),
        unreadHiddenConversationAmount: attr({
            compute() {
                const allHiddenWithThread = this.allOrderedHidden.filter(
                    chatWindow => chatWindow.thread
                );
                let amount = 0;
                for (const chatWindow of allHiddenWithThread) {
                    if (chatWindow.thread.channel && chatWindow.thread.channel.localMessageUnreadCounter > 0) {
                        amount++;
                    }
                }
                return amount;
            },
        }),
        visual: attr({
            compute() {
                let visual = JSON.parse(JSON.stringify(BASE_VISUAL));
                if (!this.messaging || !this.messaging.device) {
                    return visual;
                }
                if (!this.messaging.device.isSmall && this.messaging.discuss.discussView) {
                    return visual;
                }
                if (!this.chatWindows.length) {
                    return visual;
                }
                const relativeGlobalWindowWidth = this.messaging.device.globalWindowInnerWidth - this.startGapWidth - this.endGapWidth;
                let maxAmountWithoutHidden = Math.floor(
                    relativeGlobalWindowWidth / (this.chatWindowWidth + this.betweenGapWidth));
                let maxAmountWithHidden = Math.floor(
                    (relativeGlobalWindowWidth - this.hiddenMenuWidth - this.betweenGapWidth) /
                    (this.chatWindowWidth + this.betweenGapWidth));
                if (this.messaging.device.isSmall) {
                    maxAmountWithoutHidden = 1;
                    maxAmountWithHidden = 1;
                }
                if (this.chatWindows.length <= maxAmountWithoutHidden) {
                    // all visible
                    for (let i = 0; i < this.chatWindows.length; i++) {
                        const chatWindow = this.chatWindows[i];
                        const offset = this.startGapWidth + i * (this.chatWindowWidth + this.betweenGapWidth);
                        visual.visible.push({ chatWindow, offset });
                    }
                    visual.availableVisibleSlots = maxAmountWithoutHidden;
                } else if (maxAmountWithHidden > 0) {
                    // some visible, some hidden
                    for (let i = 0; i < maxAmountWithHidden; i++) {
                        const chatWindow = this.chatWindows[i];
                        const offset = this.startGapWidth + i * (this.chatWindowWidth + this.betweenGapWidth);
                        visual.visible.push({ chatWindow, offset });
                    }
                    if (this.chatWindows.length > maxAmountWithHidden) {
                        visual.isHiddenMenuVisible = !this.messaging.device.isSmall;
                        visual.hiddenMenuOffset = visual.visible[maxAmountWithHidden - 1].offset
                            + this.chatWindowWidth + this.betweenGapWidth;
                    }
                    for (let j = maxAmountWithHidden; j < this.chatWindows.length; j++) {
                        visual.hiddenChatWindows.push(this.chatWindows[j]);
                    }
                    visual.availableVisibleSlots = maxAmountWithHidden;
                } else {
                    // all hidden
                    visual.isHiddenMenuVisible = !this.messaging.device.isSmall;
                    visual.hiddenMenuOffset = this.startGapWidth;
                    visual.hiddenChatWindows.push(...this.chatWindows);
                    console.warn('cannot display any visible chat windows (screen is too small)');
                    visual.availableVisibleSlots = 0;
                }
                return visual;
            },
            default: BASE_VISUAL,
        }),
    },
});
