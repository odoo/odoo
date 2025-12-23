import { ChatWindow } from "@mail/core/common/chat_window_model";

import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").ChatWindow} */
const chatWindowModelPatch = {
    async _onBeforeClose() {
        await super._onBeforeClose(...arguments);
        if (
            !this.exists() ||
            this.isTransient ||
            this.channel.self_member_id?.livechat_member_type !== "visitor" ||
            this.feedbackDoneResolver
        ) {
            return;
        }
        rpc("/im_livechat/visitor_leave_session", { channel_id: this.channel.id });
        this.channel.chatbot?.stop();
        this.feedbackDoneResolver = Promise.withResolvers();
        await this.feedbackDoneResolver.promise.finally(() => (this.feedbackDoneResolver = null));
    },
};
patch(ChatWindow.prototype, chatWindowModelPatch);
