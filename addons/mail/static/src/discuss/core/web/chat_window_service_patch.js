/* @odoo-module */

import { ChatWindowService } from "@mail/core/common/chat_window_service";

import { patch } from "@web/core/utils/patch";

patch(ChatWindowService.prototype, {
    async _onClose(chatWindow, options) {
        const { notifyState = true } = options;
        await super._onClose(...arguments);
        if (notifyState) {
            this.notifyState(chatWindow);
        }
    },
    hide(chatWindow) {
        super.hide(...arguments);
        this.notifyState(chatWindow);
    },
    notifyState(chatWindow) {
        if (this.ui.isSmall) {
            return;
        }
        if (chatWindow.thread?.model === "discuss.channel") {
            chatWindow.thread.foldStateCount++;
            return this.orm.silent.call(
                "discuss.channel",
                "channel_fold",
                [[chatWindow.thread.id]],
                {
                    state: chatWindow.thread.state,
                    state_count: chatWindow.thread.foldStateCount,
                }
            );
        }
    },
    open() {
        const chatWindow = super.open(...arguments);
        this.notifyState(chatWindow);
    },
    show(chatWindow) {
        super.show(...arguments);
        this.notifyState(chatWindow);
    },
    toggleFold(chatWindow) {
        super.toggleFold(...arguments);
        this.notifyState(chatWindow);
    },
});
