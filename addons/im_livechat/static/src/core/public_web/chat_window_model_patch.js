import { ChatWindow } from "@mail/core/common/chat_window_model";
import { patch } from "@web/core/utils/patch";

patch(ChatWindow.prototype, {
    _onClose(options = {}) {
        if (
            this.thread?.channel_type === "livechat" &&
            (this.thread.livechatVisitorMember?.partner_id?.notEq(this.store.self_partner) ||
                this.thread.livechatVisitorMember?.guest_id?.notEq(this.store.self_guest))
        ) {
            const thread = this.thread; // save ref before delete
            super._onClose();
            this.delete();
            if (options.notifyState) {
                thread.leaveChannel({ force: true });
            }
        } else {
            super._onClose();
        }
    },
});
