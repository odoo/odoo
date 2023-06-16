/* @odoo-module */

import { ChatWindowService } from "@mail/core/common/chat_window_service";

import { patch } from "@web/core/utils/patch";

patch(ChatWindowService.prototype, "discuss/core/web", {
    close(chatWindow) {
        this._super(...arguments);
        this.notifyState(chatWindow);
    },
    hide(chatWindow) {
        this._super(...arguments);
        this.notifyState(chatWindow);
    },
    notifyState(chatWindow) {
        if (this.ui.isSmall) {
            return;
        }
        if (chatWindow.thread?.model === "discuss.channel") {
            return this.orm.silent.call(
                "discuss.channel",
                "channel_fold",
                [[chatWindow.thread.id]],
                {
                    state: chatWindow.thread.state,
                }
            );
        }
    },
    open() {
        const chatWindow = this._super(...arguments);
        this.notifyState(chatWindow);
    },
    show(chatWindow) {
        this._super(...arguments);
        this.notifyState(chatWindow);
    },
    toggleFold(chatWindow) {
        this._super(...arguments);
        this.notifyState(chatWindow);
    },
});
