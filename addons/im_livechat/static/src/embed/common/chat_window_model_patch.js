import { ChatWindow } from "@mail/core/common/chat_window_model";
import { patchModel } from "@mail/model/export";

import { rpc } from "@web/core/network/rpc";

export const chatWindowModelPatch = patchModel(ChatWindow, {
    async _onBeforeClose() {
        const canClose = await super._onBeforeClose(...arguments);
        if (
            !this.exists() ||
            this.isTransient ||
            this.channel.self_member_id?.livechat_member_type !== "visitor" ||
            this.feedbackDoneResolver ||
            !canClose
        ) {
            return canClose;
        }
        rpc("/im_livechat/visitor_leave_session", { channel_id: this.channel.id });
        this.channel.chatbot?.stop();
        this.feedbackDoneResolver = Promise.withResolvers();
        return await this.feedbackDoneResolver.promise.finally(
            () => (this.feedbackDoneResolver = null)
        );
    },
});
