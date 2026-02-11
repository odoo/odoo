import { ChatHub } from "@mail/core/common/chat_hub_model";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").ChatHub} */
const chatHubPatch = {
    _shouldInsertChatWindow(channel) {
        return super._shouldInsertChatWindow(channel) && !channel.readyToSwapDeferred;
    },
    _prepareChatWindowsToOpen(toOpen) {
        // Ensure cross-tab updates don't close transient channels' chatWindow as they may not exist in another tab
        toOpen.unshift(...this.opened.filter((cw) => cw.channel.isTransient && cw.notIn(toOpen)));
        return super._prepareChatWindowsToOpen(toOpen);
    },
};
patch(ChatHub.prototype, chatHubPatch);
