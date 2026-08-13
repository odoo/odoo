import { ChatWindow } from "@mail/core/common/chat_window";

import { patch } from "@web/core/utils/patch";

patch(ChatWindow.prototype, {
    async close(options) {
        const thread = this.thread;
        await super.close(options);
        if (thread?.channel_type === "livechat") {
            await thread?.isLoadedDeferred;
            if (thread.messages.length === 0) {
                thread.unpin();
            }
        }
    },
});
