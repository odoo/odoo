import { ChatWindow } from "@mail/core/common/chat_window_model";
import { patch } from "@web/core/utils/patch";

patch(ChatWindow.prototype, {
    _onClose(options = {}) {
        if (
            this.channel.channel_type === "livechat" &&
            this.channel.livechatVisitorMember?.persona?.notEq(this.store.self)
        ) {
            const channel = this.channel; // save ref before delete
            super._onClose();
            this.delete();
            if (options.notifyState) {
                channel.leaveChannel({ force: true });
            }
        } else {
            super._onClose();
        }
    },
});
