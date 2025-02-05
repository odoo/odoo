import { ChatWindow } from "@mail/core/common/chat_window_model";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").ChatWindow} */
const chatWindowPatch = {
    async _onClose(options = {}) {
        const self = await this.store.getSelf();
        if (
            this.thread?.channel_type === "livechat" &&
            this.thread.livechatVisitorMember?.persona?.notEq(self)
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
};
patch(ChatWindow.prototype, chatWindowPatch);
