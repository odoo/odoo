/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2one, one2many, one2one } from '@mail/model/model_field';
import { insertAndReplace, link, replace, unlink } from '@mail/model/model_field_command';

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
            const chatWindows = this.allOrdered;
            for (const chatWindow of chatWindows) {
                chatWindow.close();
            }
        }

        closeHiddenMenu() {
            this.update({ isHiddenMenuOpen: false });
        }

        /**
         * Closes all chat windows related to the given thread.
         *
         * @param {mail.thread} thread
         * @param {Object} [options]
         */
        closeThread(thread, options) {
            for (const chatWindow of this.chatWindows) {
                if (chatWindow.thread === thread) {
                    chatWindow.close(options);
                }
            }
        }

        openHiddenMenu() {
            this.update({ isHiddenMenuOpen: true });
        }

        openNewMessage() {
            if (!this.newMessageChatWindow) {
                this.update({ newMessageChatWindow: insertAndReplace({ manager: replace(this) }) });
            }
            this.newMessageChatWindow.makeActive();
        }

        /**
         * @param {mail.thread} thread
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
                notifyServer = !this.messaging.device.isMobile;
            }
            let chatWindow = this.chatWindows.find(chatWindow =>
                chatWindow.thread === thread
            );
            if (!chatWindow) {
                chatWindow = this.messaging.models['mail.chat_window'].create({
                    isFolded,
                    manager: link(this),
                    thread: link(thread),
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
        }

        /**
         * Shift provided chat window to previous visible index, which swap visible order of this
         * chat window and the preceding visible one
         *
         * @param {mail.chat_window} chatWindow
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
        }

        /**
         * Shift provided chat window to next visible index, which swap visible order of this
         * chat window and the following visible one.
         *
         * @param {mail.chat_window} chatWindow
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
        }

        /**
         * @param {mail.chat_window} chatWindow1
         * @param {mail.chat_window} chatWindow2
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
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {mail.chat_window[]}
         */
        _computeAllOrdered() {
            return link(this.chatWindows);
        }

        /**
         * @private
         * @returns {mail.chat_window[]}
         */
        _computeAllOrderedHidden() {
            return replace(this.visual.hidden.chatWindowLocalIds.map(chatWindowLocalId =>
                this.messaging.models['mail.chat_window'].get(chatWindowLocalId)
            ));
        }

        /**
         * @private
         * @returns {mail.chat_window[]}
         */
        _computeAllOrderedVisible() {
            return replace(this.visual.visible.map(({ chatWindowLocalId }) =>
                this.messaging.models['mail.chat_window'].get(chatWindowLocalId)
            ));
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasHiddenChatWindows() {
            return this.allOrderedHidden.length > 0;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasVisibleChatWindows() {
            return this.allOrderedVisible.length > 0;
        }

        /**
         * @private
         * @returns {mail.chat_window|undefined}
         */
        _computeLastVisible() {
            const { length: l, [l - 1]: lastVisible } = this.allOrderedVisible;
            if (!lastVisible) {
                return unlink();
            }
            return link(lastVisible);
        }

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
        }

        /**
         * @private
         * @returns {Object}
         */
        _computeVisual() {
            let visual = JSON.parse(JSON.stringify(BASE_VISUAL));
            if (!this.messaging || !this.messaging.device) {
                return visual;
            }
            const device = this.messaging.device;
            const discuss = this.messaging.discuss;
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
         * List of ordered chat windows.
         */
        allOrdered: one2many('mail.chat_window', {
            compute: '_computeAllOrdered',
        }),
        allOrderedHidden: one2many('mail.chat_window', {
            compute: '_computeAllOrderedHidden',
        }),
        allOrderedVisible: one2many('mail.chat_window', {
            compute: '_computeAllOrderedVisible',
        }),
        chatWindows: one2many('mail.chat_window', {
            inverse: 'manager',
            isCausal: true,
        }),
        hasHiddenChatWindows: attr({
            compute: '_computeHasHiddenChatWindows',
        }),
        hasVisibleChatWindows: attr({
            compute: '_computeHasVisibleChatWindows',
        }),
        isHiddenMenuOpen: attr({
            default: false,
        }),
        lastVisible: many2one('mail.chat_window', {
            compute: '_computeLastVisible',
        }),
        newMessageChatWindow: one2one('mail.chat_window', {
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
    };
    ChatWindowManager.identifyingFields = ['messaging'];
    ChatWindowManager.modelName = 'mail.chat_window_manager';

    return ChatWindowManager;
}

registerNewModel('mail.chat_window_manager', factory);
