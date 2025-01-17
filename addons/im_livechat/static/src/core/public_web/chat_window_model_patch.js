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
            param1.notifyState = false;
            super._onClose(param1, ...args);
            this.delete();
            if (!param1.noLeaveChannel) {
                thread.leaveChannel({ force: true });
            }
            return;
        }
        return super._onClose(param1, ...args);
    },
});
