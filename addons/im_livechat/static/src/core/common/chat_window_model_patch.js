import { ChatWindow } from "@mail/core/common/chat_window_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").ChatWindow} */
const chatWindowPatch = {
    setup() {
        super.setup(...arguments);
        /** @type {PromiseWithResolvers<boolean>} */
        this.confirmCloseResolver = null;
        /** @type {PromiseWithResolvers<void>} */
        this.feedbackDoneResolver = null;
    },
    async _canClose() {
        if (!this.exists() || this.channel?.channel_type !== "livechat") {
            return super._canClose(...arguments);
        }
        if (
            !this.channel.livechatShouldAskLeaveConfirmation ||
            this.confirmCloseResolver ||
            this.feedbackDoneResolver
        ) {
            this.confirmCloseResolver = null;
            return true;
        }
        if (!this.isOpen) {
            this.open();
        }
        this.confirmCloseResolver = Promise.withResolvers();
        return this.confirmCloseResolver.promise.finally(() => (this.confirmCloseResolver = null));
    },
};
patch(ChatWindow.prototype, chatWindowPatch);
