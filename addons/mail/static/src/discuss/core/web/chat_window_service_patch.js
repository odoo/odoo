/* @odoo-module */

import { ChatWindowService } from "@mail/core/common/chat_window_service";

import { patch } from "@web/core/utils/patch";

<<<<<<< HEAD
patch(ChatWindowService.prototype, {
    async _onClose(chatWindow, options) {
        const { notifyState = true } = options;
        await super._onClose(...arguments);
        if (notifyState) {
            this.notifyState(chatWindow);
        }
||||||| parent of 16d7f417311 (temp)
patch(ChatWindowService.prototype, "discuss/core/web", {
    close(chatWindow) {
        this._super(...arguments);
        this.notifyState(chatWindow);
=======
patch(ChatWindowService.prototype, "discuss/core/web", {
    close(chatWindow, { notifyState = true } = {}) {
        this._super(...arguments);
        if (notifyState) {
            this.notifyState(chatWindow);
        }
>>>>>>> 16d7f417311 (temp)
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
<<<<<<< HEAD
                    state_count: chatWindow.thread.foldStateCount,
||||||| parent of 16d7f417311 (temp)
=======
                    context: { state_count: chatWindow.thread.foldStateCount },
>>>>>>> 16d7f417311 (temp)
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
