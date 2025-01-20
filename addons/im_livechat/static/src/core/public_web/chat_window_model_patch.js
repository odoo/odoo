import { ChatWindow } from "@mail/core/common/chat_window_model";
import { patch } from "@web/core/utils/patch";

patch(ChatWindow.prototype, {
    async _onClose(param1 = {}, ...args) {
        const thread = this.thread;
        if (!thread) {
            return super._onClose(param1, ...args);
        }
        if (
            thread.channel_type === "livechat" &&
            thread.livechatVisitorMember?.persona?.notEq(this.store.self)
        ) {
            if (param1.notifyState) {
                thread.leaveChannel({ force: true });
            }
            param1.notifyState = false;
            super._onClose(param1, ...args);
            this.delete();
            return;
        }
        return super._onClose(param1, ...args);
    },
});
